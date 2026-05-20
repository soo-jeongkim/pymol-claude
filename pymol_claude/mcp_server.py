"""FastMCP server exposing PyMOL's cmd module as MCP tools."""

from __future__ import annotations

import io
import os
import tempfile
import threading
from contextlib import redirect_stdout
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from pymol_claude.metrics import StructureRecord
from pymol_claude.triage import TriageState

pymol_lock = threading.Lock()
triage = TriageState()

PLDDT_PALETTE = "red_yellow_green_cyan_blue"


def ensure_pymol():
    """Import pymol.cmd, raising a clear error if unavailable."""
    try:
        from pymol import cmd
        return cmd
    except ImportError:
        raise RuntimeError(
            "PyMOL is not installed. Install it with: "
            "/Applications/PyMOL.app/Contents/bin/python -m pip install -e ."
        )


def apply_plddt_palette(cmd, selection: str = "all") -> None:
    """Color selection by pLDDT (b-factor 0–100, project palette)."""
    cmd.spectrum("b", PLDDT_PALETTE, selection, 0, 100)


def render_image(width: int, height: int, ray: bool = False) -> Image:
    """Render current PyMOL view to an Image. Must be called with pymol_lock held."""
    cmd = ensure_pymol()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        if ray:
            cmd.ray(width, height)
        else:
            cmd.draw(width, height, antialias=2)
        cmd.png(tmp_path, dpi=150)

        # PyMOL's png command may be async; wait for file
        import time
        for _ in range(50):
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                break
            time.sleep(0.1)

        data = Path(tmp_path).read_bytes()
        return Image(data=data, format="png")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def triage_render(path: Path, width: int = 800, height: int = 600) -> Image:
    """Focus on `path` (loading it if needed), hide siblings, color by pLDDT, render.
    Must be called with pymol_lock held."""
    cmd = ensure_pymol()
    obj_name = path.stem
    if obj_name not in cmd.get_object_list():
        cmd.load(str(path), obj_name)
    cmd.disable("all")
    cmd.enable(obj_name)
    cmd.show("cartoon", obj_name)
    cmd.hide("lines", obj_name)
    apply_plddt_palette(cmd, obj_name)
    cmd.orient(obj_name)
    cmd.bg_color("white")
    return render_image(width, height, ray=False)


def create_server() -> FastMCP:
    """Create and configure the FastMCP server with all PyMOL tools."""

    mcp = FastMCP(
        "pymol-claude",
        instructions=(
            "You are a PyMOL assistant with direct control of a running PyMOL session. "
            "When the user asks you to do something visual — color, align, show, hide — DO IT. "
            "Don't describe; execute.\n\n"
            "The main tool is `run(code)`: arbitrary Python with `cmd` (pymol.cmd) bound. "
            "Use it for every PyMOL operation that isn't rendering, metrics, or triage. "
            "Examples:\n"
            "  run(\"cmd.load('foo.cif')\")\n"
            "  run(\"cmd.show('cartoon'); cmd.color('salmon', 'chain A')\")\n"
            "  print(...) inside the code to return values.\n\n"
            "Use the dedicated tools for things `run` can't do:\n"
            "- render / snapshot — return a PNG inline\n"
            "- color_by_plddt — applies the project's pLDDT palette\n"
            "- get_metrics / find_low_confidence / compare_all / cif_grep — gemmi, not PyMOL\n"
            "- load_directory / next_structure / prev_structure / go_to / current / "
            "flag / show_flags / export_flags / filter — triage workflow (stateful + renders)\n\n"
            "Conventions:\n"
            "- B-factor on predicted structures is pLDDT (0-100). Call it pLDDT.\n"
            "- For pLDDT coloring use the `color_by_plddt` tool (don't reinvent the palette).\n"
            "- Selection syntax: 'chain A', 'resi 45-67', 'chain A and resi 45-67', "
            "'name CA', 'polymer', 'organic', 'all'.\n"
            "- When triaging (next/prev/flag), always report mean pLDDT and ipTM alongside the image."
        ),
    )

    # ── Rendering ──────────────────────────────────────────────────────────

    @mcp.tool()
    def color_by_plddt(selection: str = "all") -> str:
        """Color by pLDDT (B-factor 0–100) with the project palette: blue=high, red=low."""
        cmd = ensure_pymol()
        with pymol_lock:
            apply_plddt_palette(cmd, selection)
            return f"Colored {selection} by pLDDT"

    @mcp.tool()
    def render(width: int = 800, height: int = 600, ray: bool = True) -> Image:
        """Render current view as an image. ray=True for high quality (slower)."""
        with pymol_lock:
            return render_image(width, height, ray=ray)

    @mcp.tool()
    def snapshot(width: int = 800, height: int = 600) -> Image:
        """Quick snapshot without ray tracing. Faster, lower quality."""
        with pymol_lock:
            return render_image(width, height, ray=False)

    # ── Metrics (gemmi) ────────────────────────────────────────────────────

    @mcp.tool()
    def get_metrics(name: str = "") -> str:
        """Get detailed structure metrics (pLDDT, ipTM, pTM, PAE)."""
        cmd = ensure_pymol()

        with pymol_lock:
            objects = cmd.get_object_list()
        if not objects:
            return "No objects loaded"
        if name and name not in objects:
            return f"Object '{name}' not found. Loaded: {', '.join(objects)}"

        targets = [name] if name else objects
        results = []
        for obj_name in targets:
            record = triage.record_for_obj(obj_name)
            if record is None:
                results.append(f"{obj_name}: no metrics available (load via triage or provide file path)")
            else:
                results.append(record.format_report())
        return "\n\n".join(results)

    @mcp.tool()
    def find_low_confidence(name: str = "", threshold: int = 70) -> str:
        """Find contiguous low-pLDDT regions in a structure."""
        from pymol_claude.metrics import find_low_confidence as find_low

        if name:
            record = triage.record_for_obj(name)
            if record is None:
                return f"No metrics for '{name}'. Load the structure directory first."
            return find_low(record, threshold)

        cmd = ensure_pymol()
        with pymol_lock:
            objects = cmd.get_object_list()
        if not objects:
            return "No objects loaded"

        results = []
        for obj in objects:
            record = triage.record_for_obj(obj)
            if record is None:
                results.append(f"{obj}: no metrics available")
            else:
                results.append(find_low(record, threshold))
        return "\n\n".join(results)

    @mcp.tool()
    def compare_all() -> str:
        """Compare all loaded objects by pLDDT — sorted table."""
        if not triage.records:
            return "No structures loaded in triage. Use load_directory first."

        records = sorted(triage.records.values(), key=StructureRecord.sort_key, reverse=True)

        lines = [f"{'Name':<30} {'pLDDT':>8} {'ipTM':>8} {'pTM':>8} {'Chains':>6} {'Res':>6}"]
        lines.append("-" * 70)
        for r in records:
            plddt = f"{r.mean_plddt:.1f}" if r.mean_plddt is not None else "—"
            iptm = f"{r.iptm:.3f}" if r.iptm is not None else "—"
            ptm = f"{r.ptm:.3f}" if r.ptm is not None else "—"
            lines.append(
                f"{r.name:<30} {plddt:>8} {iptm:>8} {ptm:>8} {len(r.chains):>6} {r.n_residues:>6}"
            )
        return "\n".join(lines)

    # ── Triage ─────────────────────────────────────────────────────────────

    @mcp.tool()
    def load_directory(path: str) -> str:
        """Scan a directory for structure files, extract metrics, and load all into PyMOL. Sets up triage navigation."""
        cmd = ensure_pymol()
        msg = triage.load_directory(path)
        if not triage.files:
            return msg
        with pymol_lock:
            cmd.delete("all")
            for f in triage.files:
                cmd.load(str(f), f.stem)
        return msg

    @mcp.tool()
    def next_structure() -> Image:
        """Advance to next structure, load it, color by pLDDT, and render."""
        p = triage.next()
        if p is None:
            raise ValueError("No structures loaded. Use load_directory first.")
        with pymol_lock:
            return triage_render(p)

    @mcp.tool()
    def prev_structure() -> Image:
        """Go back to previous structure, load it, color by pLDDT, and render."""
        p = triage.prev()
        if p is None:
            raise ValueError("No structures loaded. Use load_directory first.")
        with pymol_lock:
            return triage_render(p)

    @mcp.tool()
    def go_to(number: int) -> Image:
        """Jump to Nth structure (1-indexed), load it, and render."""
        p = triage.go_to(number)
        if p is None:
            raise ValueError("No structures loaded. Use load_directory first.")
        with pymol_lock:
            return triage_render(p)

    @mcp.tool()
    def current() -> Image:
        """Re-render the current structure without advancing."""
        p = triage.current_path()
        if p is None:
            raise ValueError("No structures loaded. Use load_directory first.")
        with pymol_lock:
            return triage_render(p)

    @mcp.tool()
    def flag(note: str = "") -> str:
        """Flag the current structure with an optional note."""
        return triage.flag(note)

    @mcp.tool()
    def show_flags() -> str:
        """List all flagged structures."""
        return triage.show_flags()

    @mcp.tool()
    def export_flags() -> str:
        """Export all flags as JSON (with metrics)."""
        return triage.export_flags()

    @mcp.tool()
    def filter(min_plddt: float, max_plddt: float, include_unscored: bool = False) -> str:
        """Filter triage structures by pLDDT range. Unscored records excluded unless include_unscored=True."""
        return triage.filter(min_plddt, max_plddt, include_unscored)

    # ── File inspection ────────────────────────────────────────────────────

    @mcp.tool()
    def cif_grep(tag: str, path: str = ".") -> str:
        """Search CIF files for a tag's value (e.g. '_ma_qa_metric_global.metric_value'). path may be a file or a directory (recursed on *.cif)."""
        import gemmi
        p = Path(path).expanduser()
        if p.is_dir():
            targets = sorted(p.rglob("*.cif"))
        elif p.is_file():
            targets = [p]
        else:
            return f"Not found: {p}"
        if not targets:
            return f"No .cif files under {p}"

        if "." in tag:
            category, _, item = tag.rpartition(".")
            category = category + "."
        else:
            category, item = None, tag

        lines = []
        for f in targets:
            try:
                doc = gemmi.cif.read(str(f))
            except (RuntimeError, ValueError) as e:
                lines.append(f"{f.name}: <parse error: {e}>")
                continue
            for block in doc:
                if category is not None:
                    for row in block.find(category, [item]):
                        lines.append(f"{f.name}: {row[0]}")
                else:
                    v = block.find_value(tag)
                    if v is not None:
                        lines.append(f"{f.name}: {v}")
        return "\n".join(lines) or "No matches"

    # ── Escape hatch ───────────────────────────────────────────────────────

    @mcp.tool()
    def run(code: str) -> str:
        """Execute Python code. `cmd` is the PyMOL command module; use `cmd.do(...)` for PyMOL CLI syntax. Output from print() is returned."""
        cmd = ensure_pymol()
        buf = io.StringIO()
        with pymol_lock:
            try:
                with redirect_stdout(buf):
                    exec(code, {"cmd": cmd, "__builtins__": __builtins__})
            except Exception as e:
                return f"Error: {e}"
        output = buf.getvalue()
        return output if output.strip() else "OK"

    return mcp
