# pymol-claude

PyMOL plugin that exposes PyMOL as an MCP server. Control PyMOL from Claude Code, Cursor, or any MCP client — load structures, color, align, render — all from the terminal.

## Setup (one time)

### 1. Clone this repo

```bash
git clone <repo-url> pymol-claude
cd pymol-claude
```

### 2. Install into PyMOL's Python

```bash
/Applications/PyMOL.app/Contents/bin/python -m pip install -e .
```

This installs the plugin into PyMOL's Python and puts the `pymol-claude` CLI in PyMOL's `bin/` directory (e.g. `/Applications/PyMOL.app/Contents/bin/pymol-claude`). On Linux/conda, replace the Python path with your PyMOL interpreter.

`sudo` is usually unnecessary and best avoided.

### 3. Tell PyMOL to start the plugin on launch

Add this once to `~/.pymolrc.py`:

```python
from pymol_claude import __init_plugin__
__init_plugin__()
```

Restart PyMOL. The console should print `MCP server running on http://127.0.0.1:8766/sse`.

### 4. Connect your MCP client (one-time, global)

Goal: set this up once so the `pymol` tools are available in every Cursor / Claude Code window, in any directory. You shouldn't have to `cd` into this repo to use the tool.

#### Cursor

```bash
/Applications/PyMOL.app/Contents/bin/pymol-claude install-config
```

This writes `~/.cursor/mcp.json` (merging with any existing entries — your other MCP servers are preserved). Restart Cursor; verify under Settings → Cursor Settings → MCP that `pymol` is listed.

If `pymol-claude` isn't on your `$PATH`, either use the absolute path above or add `/Applications/PyMOL.app/Contents/bin` to your PATH.

#### Claude Code

```bash
claude mcp add --transport sse --scope user pymol http://localhost:8766/sse
```

Works from any directory. Same effect: every Claude Code session sees the `pymol` server.

#### Don't want to install with pip?

You can run the plugin directly from the clone by using `sys.path` injection in `~/.pymolrc.py`:

```python
import sys
sys.path.insert(0, "/path/to/pymol-claude")
from pymol_claude import __init_plugin__
__init_plugin__()
```

In that case run `python -m pymol_claude.cli install-config` from inside the clone instead of the absolute-path command above.

#### Project-scoped config

If you specifically want the `pymol` server enabled only inside one project (rather than globally), use:

```bash
pymol-claude install-config --project --project-dir /path/to/project
```

This writes `<project>/.cursor/mcp.json`. Cursor merges project and global configs; project-level entries override the global `pymol` entry inside that workspace, which is occasionally what you want (e.g. point at a different port for that project) and otherwise should be avoided to prevent surprises.

## Usage

1. **Open PyMOL** — the MCP server auto-starts (check console for "MCP server running on...")
2. **Open your MCP client**
   - Claude Code in any terminal: `claude`
   - Cursor in the IDE with MCP enabled
3. **Talk to it:**
   - "Load all the CIF files in <your structure dir>"
   - "Color by pLDDT"
   - "Align model_0 to model_1"
   - "Show sticks for the active site"
   - "Render an image"

PyMOL must be running first — it's the server, and your MCP client (Claude Code or Cursor) is the client.

### Phone / remote use

Any MCP client session that can reach the MCP port can drive PyMOL. Claude Code sessions — including ones started remotely from the Claude mobile app — work well for this. So you can leave PyMOL running on your workstation and triage structures from your phone:

- "Load the latest fold batch and tell me which model has the best pLDDT"
- "Any low-confidence loops in model 3?"
- "Color by chain and render"

Metrics (pLDDT, ipTM, pTM, PAE) are extracted by **gemmi** straight from the mmCIF — no render needed — so you get fast text answers, and your MCP client does the actual analysis (sorting, comparing, flagging) on top of those numbers. Renders come back inline as PNGs when you ask for them.

### Reusing your existing PyMOL scripts

You can point your MCP client at a `.py` file full of your own PyMOL functions and ask it to apply them. It reads the script, lists what's in there, and runs the function bodies for you through the `run` tool — defining any custom colors or settings the script depends on.

Example:

> "Look at `~/scripts/my_pymol_helpers.py` — what view templates do you have? Apply the publication-style one to all loaded objects."

Your MCP client will scan the script, summarize the available functions (e.g. `pic`, `pic2`, `ball_and_stick`, `bspec1`, ...), then execute the chosen one against your current session. Useful for porting old `.pymolrc` setups or lab-specific styling presets without rewriting them as MCP tools.

## Available tools

The main tool is **`run(code)`** — arbitrary Python with `cmd` (pymol.cmd) bound. Your MCP client writes the PyMOL itself rather than calling a wrapper for every verb: `run("cmd.load('foo.cif'); cmd.show('cartoon'); cmd.color('salmon', 'chain A')")`.

The dedicated tools cover what `run` can't:

**Rendering (return PNGs inline):** `render` (ray-traced), `snapshot` (fast), `color_by_plddt` (project palette)

**Metrics (gemmi, not PyMOL):** `get_metrics`, `find_low_confidence`, `compare_all`, `cif_grep`

**Triage (stateful navigation + rendered images):** `load_directory`, `next_structure`, `prev_structure`, `go_to`, `current`, `flag`, `show_flags`, `export_flags`, `filter`

## PyMOL commands

```
start_mcp [port]   # Start MCP server (auto-starts on plugin load)
stop_mcp           # Stop MCP server
```
