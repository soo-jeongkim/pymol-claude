"""CLI for pymol-claude setup and diagnostics.

Subcommands:
    install-config     Write Cursor MCP config (global by default)

The CLI is pure stdlib — it does not import pymol or fastmcp — so it can run
under any Python interpreter, even if the plugin itself was installed into
PyMOL's bundled Python.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

DEFAULT_PORT = 8766


def server_url(port: int) -> str:
    return f"http://localhost:{port}/sse"


def _load_existing(path: Path) -> tuple[dict, str | None]:
    """Return (data, error). data is {} if file is missing."""
    if not path.exists():
        return {}, None
    try:
        text = path.read_text()
    except OSError as e:
        return {}, f"Could not read {path}: {e}"
    if not text.strip():
        return {}, None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return {}, f"{path} is not valid JSON: {e}. Fix or remove it, then re-run."
    if not isinstance(data, dict):
        return {}, f"{path} must contain a JSON object at the top level."
    return data, None


def write_mcp_config(path: Path, port: int) -> str:
    """Merge a `pymol` entry into mcpServers, preserving other servers.

    Returns a human-readable status message. Raises on I/O errors.
    """
    data, err = _load_existing(path)
    if err is not None:
        return f"ERROR: {err}"

    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return f"ERROR: 'mcpServers' in {path} must be an object."

    desired_url = server_url(port)
    existing = servers.get("pymol")
    if isinstance(existing, dict) and existing.get("url") == desired_url:
        return f"Already configured: {path} -> pymol @ {desired_url}"

    servers["pymol"] = {"url": desired_url}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")

    action = "Updated" if existing is not None else "Wrote"
    return f"{action} {path} -> pymol @ {desired_url}"


def cmd_install_config(args: argparse.Namespace) -> int:
    if args.project:
        target = Path(args.project_dir).resolve() / ".cursor" / "mcp.json"
    else:
        target = Path.home() / ".cursor" / "mcp.json"

    msg = write_mcp_config(target, args.port)
    print(msg)
    if msg.startswith("ERROR"):
        return 1
    if not args.project:
        print("Restart Cursor to pick up the change.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pymol-claude",
        description="pymol-claude setup and diagnostics",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_install = sub.add_parser(
        "install-config",
        help="Write Cursor MCP config so the pymol server is available everywhere",
        description=(
            "Write Cursor MCP config. Default target is ~/.cursor/mcp.json (global), "
            "which makes the pymol tools available in every Cursor window. "
            "Use --project to write ./.cursor/mcp.json instead. "
            "Existing entries in mcpServers are preserved."
        ),
    )
    p_install.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"MCP server port (default: {DEFAULT_PORT})",
    )
    p_install.add_argument(
        "--project",
        action="store_true",
        help="Write project-level config (./.cursor/mcp.json) instead of global",
    )
    p_install.add_argument(
        "--project-dir",
        default=".",
        help="Project root for --project (default: current directory)",
    )
    p_install.set_defaults(func=cmd_install_config)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
