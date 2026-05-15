# pymol-claude

PyMOL plugin that exposes PyMOL's Python API as an MCP server.

## Architecture

- **Plugin runs inside PyMOL's process.** On startup (`__init_plugin__`), a FastMCP server launches in a daemon background thread on port 8766.
- **MCP server** (`pymol_claude/mcp_server.py`) exposes PyMOL's `cmd` module as MCP tools. Claude connects via `http://localhost:8766/sse`.
- **Metrics** (`pymol_claude/metrics.py`) uses gemmi for structure metadata extraction — not PyMOL. This keeps metric parsing clean and avoids polluting PyMOL's object state. Reads PAE/ipTM/pTM from `_ma_qa_metric_*` categories in mmCIF first, falls back to sibling JSON.
- **Triage** (`pymol_claude/triage.py`) manages navigation/flagging state for reviewing batches of structures (mobile eval workflow).

## Thread safety

All `pymol.cmd` calls are serialized with `pymol_lock` (a `threading.Lock`). The MCP server runs in a daemon thread; PyMOL's GUI runs on the main thread. Rendering (`cmd.ray`, `cmd.png`) definitely needs the lock. Most read operations work from threads in modern PyMOL, but we lock everything for safety.

## How to test

1. Install: `/Applications/PyMOL.app/Contents/bin/python -m pip install -e .`
2. Start PyMOL (GUI): plugin auto-starts, check console for "MCP server running on..."
3. Or headless: `pymol -cq -r start_headless.py -- --port 8766`
4. Test with curl: `curl http://localhost:8766/sse` should establish SSE connection
5. Connect Claude Code: add `"pymol": {"url": "http://localhost:8766/sse"}` to MCP settings

## How to add new tools

1. Open `pymol_claude/mcp_server.py`
2. Inside `create_server()`, add a new function decorated with `@mcp.tool()`
3. Use `pymol_lock` for any `pymol.cmd` calls
4. Return a string (status message) or `Image` (for rendered output)

```python
@mcp.tool()
def my_new_tool(arg: str) -> str:
    """Description shown to Claude."""
    cmd = ensure_pymol()
    with pymol_lock:
        cmd.some_operation(arg)
        return f"Done: {arg}"
```

## Dependencies

- `fastmcp>=2.0` — MCP server framework
- `gemmi>=0.6` — mmCIF/PDB parsing for metrics (atom data + AF3 `_ma_qa_metric_*`)
- `numpy`, `scipy`, `rich` — supporting libraries
- PyMOL — **not a pip dependency**, install the app from pymol.org. Install this plugin into PyMOL's Python: `/Applications/PyMOL.app/Contents/bin/python -m pip install -e .`
