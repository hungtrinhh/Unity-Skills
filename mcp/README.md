# Unity-Skills MCP Server

Dedicated Model Context Protocol (MCP) server for **Unity-Skills**.
Exposes the complete suite of Unity-Skills (800+ operations) running in your Unity Editor via FastMCP stdio interface.

## Quickstart

Run directly with `uv`:
```bash
uv run --directory D:/MCP/Unity-Skills/mcp server.py
```

## Tools Provided

- `get_editor_health()`: Check if Unity Editor is connected, get scene name, compile status, and active mode.
- `search_skills(intent)`: Find matching skills for your goal using Unity-Skills intent recommendation.
- `execute_skill(skill_name, args)`: Call any Unity skill (e.g. `create_gameobject`, `find_gameobjects`, etc.).
- `dry_run_skill(skill_name, args)`: Preview parameters and validate without executing mutations.
- `batch_skills(steps, continue_on_error)`: Execute multiple skill operations atomically.
- `get_skill_schema(category)`: Retrieve schema and parameters for skills.
- `diagnose_editor()`: Capture comprehensive Editor diagnostics (console errors, warnings, jobs).
