# MCP bridge (optional)

`scripts/unity_skills_mcp.py` exposes the REST skills to MCP-aware agents over stdio, so Unity appears in the
agent's tool list without the skill having to trigger. It wraps `unity_skills.py`, so port discovery
(`registry.json` + 8090-8100 scan) and retries are unchanged and a port change after a domain reload is invisible.

Install: installing the Claude Code skill from the UnitySkills panel also writes `<project>/.mcp.json`:

```json
{ "mcpServers": { "unity-skills": { "command": "python", "args": ["<abs path>/scripts/unity_skills_mcp.py"] } } }
```

Claude Code asks once to approve a project-scoped server. Other clients: register the same command by hand
(`python3` on macOS/Linux). Requires Python 3 with `requests`.

## Tools

| Tool | Purpose |
|------|---------|
| `unity_status` | `/health` of the connected editor plus every registered instance |
| `unity_find_skills` | keyword search (name, description, category); every term must match |
| `unity_skill_info` | exact parameter schema of one skill |
| `unity_call` | run one skill: `skill`, `params`, optional `wait_for_job`, `dry_run_token` |
| `unity_batch` | `steps` of `{skill, args}`, optional `continue_on_error`, `mode` (`dryRun`/`transactional`), `diff` |

Only these five tools are listed, not the 800+ skills, to keep the agent's context small. Operating mode,
permissions, dry-run gating and audit still apply server-side: a gated call returns the same structured error
(`errorCode`, `suggestedFixes`) with `isError: true`.

Flow: `unity_find_skills` -> `unity_skill_info` -> `unity_call`.
