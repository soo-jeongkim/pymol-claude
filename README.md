# pymol-claude

PyMOL plugin that exposes PyMOL as an MCP server. Control PyMOL from Claude Code — load structures, color, align, render — all from the terminal.

## Setup (one time)

### 1. Clone this repo

```bash
git clone <repo-url> pymol-claude
cd pymol-claude
```

### 2. Install into PyMOL's bundled Python

PyMOL ships its own Python; install the plugin into *that* interpreter, not your system Python. On macOS with PyMOL.app:

```bash
sudo /Applications/PyMOL.app/Contents/bin/python -m pip install -e .
```

On Linux/conda installs, replace the path with wherever your PyMOL keeps its Python (e.g. `$(which pymol | xargs dirname)/python`).

### 3. Auto-start the plugin with PyMOL

Append a launcher to `~/.pymolrc.py`. Run this from inside the clone — `$(pwd)` is captured into the rc file:

```bash
cat >> ~/.pymolrc.py <<EOF
import sys
sys.path.insert(0, "$(pwd)")
from pymol_claude import __init_plugin__
__init_plugin__()
EOF
```

### 4. Register the MCP server with Claude Code

```bash
claude mcp add --transport sse --scope user pymol http://localhost:8766/sse
```

That's it. This works globally — you can run `claude` from any directory.

## Usage

1. **Open PyMOL** — the MCP server auto-starts (check console for "MCP server running on...")
2. **Open Claude Code** in any terminal: `claude`
3. **Talk to it:**
   - "Load all the CIF files in <your structure dir>"
   - "Color by pLDDT"
   - "Align model_0 to model_1"
   - "Show sticks for the active site"
   - "Render an image"

PyMOL must be running first — it's the server, Claude is the client.

## Available tools

**Visualization:** load, delete, list_objects, show, hide, color, color_by_plddt, color_by_chain, color_by_spectrum, select, zoom, center, orient, turn, bg_color, set_setting

**Structural analysis:** align, super_align, polar_contacts, measure, get_sequence, get_chains, count_atoms

**Rendering:** render (ray-traced), snapshot (fast)

**Metrics (gemmi):** get_metrics, find_low_confidence, compare_all

**Triage:** load_directory, next_structure, prev_structure, go_to, current, flag, show_flags, export_flags, filter

**Escape hatch:** run (arbitrary PyMOL/Python code)

## PyMOL commands

```
start_claude [port]   # Start MCP server (auto-starts on plugin load)
stop_claude           # Stop MCP server
```
