# pymol-claude

PyMOL plugin that exposes PyMOL as an MCP server. Control PyMOL from Claude Code — load structures, color, align, render — all from the terminal.

## Setup (one time)

### 1. Install dependencies into PyMOL's Python

```bash
sudo /Applications/PyMOL.app/Contents/bin/python -m pip install -e ~/Documents/pymol-claude
```

### 2. Auto-start the plugin with PyMOL

```bash
echo 'import sys; sys.path.insert(0, "/Users/$USER/Documents/pymol-claude"); from pymol_claude import __init_plugin__; __init_plugin__()' > ~/.pymolrc.py
```

### 3. Register the MCP server with Claude Code

```bash
claude mcp add --transport sse --scope user pymol http://localhost:8766/sse
```

That's it. This works globally — you can run `claude` from any directory.

## Usage

1. **Open PyMOL** — the MCP server auto-starts (check console for "MCP server running on...")
2. **Open Claude Code** in any terminal: `claude`
3. **Talk to it:**
   - "Load all the CIF files in ~/Documents/foldspace/foldspace/test"
   - "Color by pLDDT"
   - "Align model_0 to model_1"
   - "Show sticks for the active site"
   - "Render an image"

PyMOL must be running first — it's the server, Claude is the client.

## Available tools

**Visualization:** load, delete, list_objects, show, hide, color, color_by_plddt, color_by_chain, color_by_spectrum, select, zoom, center, orient, turn, bg_color, set_setting

**Structural analysis:** align, super_align, polar_contacts, measure, get_sequence, get_chains, count_atoms

**Rendering:** render (ray-traced), snapshot (fast)

**Metrics (biotite):** get_metrics, find_low_confidence, compare_all

**Triage:** load_directory, next_structure, prev_structure, go_to, current, flag, show_flags, export_flags, filter

**Escape hatch:** run (arbitrary PyMOL/Python code)

## PyMOL commands

```
start_claude [port]   # Start MCP server (auto-starts on plugin load)
stop_claude           # Stop MCP server
```
