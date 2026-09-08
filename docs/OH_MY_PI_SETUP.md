# Oh My Pi (OMP) Integration Guide

This guide describes how to configure and use **Oh My Pi (OMP)** with **Unity-Skills** and **Unity MCP servers**.

---

## 1. Overview & Architecture

Oh My Pi can interact with Unity via two complementary mechanisms:
1. **Unity-Skills REST API (Port 8090)**: Fast, comprehensive direct REST integration driving Unity Editor automation via local HTTP requests. Unity-Skills is driven directly as an AI Skill (via `.omp/skills/unity-skills` or Open Agent Skills), not via an MCP server entry.
2. **Model Context Protocol (MCP)**: Standardized MCP tools configured in `.omp/mcp.json` (`unity-cli` stdio server). (Optional: `unityMCP` HTTP server on port 8080 only if using the separate `MCPForUnity` package and its server is running).

---

## 2. Unity-Skills REST Server Workflow (Port 8090)

The Unity-Skills package runs an embedded REST service inside the Unity Editor on port `8090`:
- **Skill Location**: Place `SKILL.md` (or symlink) in `~/.agents/skills/unity-skills` or `.omp/skills/unity-skills`.
- **Unity Package**: Ensure the `UnitySkills` package is installed in your Unity project (via UPM or embedded in `Packages/`).
- **REST Port**: `http://127.0.0.1:8090/`
- **Workflow**:
  - Open your Unity project in the Unity Editor.
  - The UnitySkills background service starts and listens on port `8090`.
  - Oh My Pi reads `SKILL.md` instructions and issues direct HTTP requests or executes skill scripts against the REST endpoints.

---

## 3. MCP Configuration (`.omp/mcp.json`)

Oh My Pi supports project-level MCP configuration in `.omp/mcp.json` or global configuration in `~/.omp/agent/mcp.json`.

### Project Configuration (`.omp/mcp.json`)

Create `.omp/mcp.json` in your repository root:

```json
{
  "$schema": "https://raw.githubusercontent.com/can1357/oh-my-pi/main/packages/coding-agent/src/config/mcp-schema.json",
  "mcpServers": {
    "unity-cli": {
      "type": "stdio",
      "command": "unity",
      "args": [
        "mcp",
        "--project-path",
        "${CWD}"
      ]
    }
  }
}
```

*(Note: Do not add `unityMCP` on `http://127.0.0.1:8080/mcp` unless you are running the separate `MCPForUnity` package and have started its server in Unity via `Window > MCP for Unity`. Unity-Skills uses port 8090 REST API directly as an AI Skill).*

### Server Details

- **`unity-cli` (stdio)**:
  - Runs the Unity command-line MCP interface (`unity mcp --project-path <path>`).
  - `${CWD}` dynamically expands to the current project directory.
  - Used for headless CLI commands, project management, and editor operations via stdio.
- **`unityMCP` (http - optional)**:
  - Connects to the separate Unity MCP (MCPForUnity) HTTP endpoint at `http://127.0.0.1:8080/mcp`.
  - Requires manually opening `Window > MCP for Unity` and clicking "Start Server" in the Editor. If the server is not running, OMP startup will fail to connect.
---

## 4. Oh My Pi MCP Commands

In the Oh My Pi terminal or interactive chat session, use the following commands to manage and test MCP servers:

- `/mcp list`: List all discovered and active MCP servers and their available tools.
- `/mcp reload`: Reload MCP server configuration from `.omp/mcp.json` and restart connections.
- `/mcp test <name>`: Test connectivity and tool registration for a specific MCP server (e.g., `/mcp test unity-cli`).

---

## 5. Summary of Ports & Paths

| Service | Protocol / Type | Default Address / Path | Config / Skill Path |
|---|---|---|---|
| **Unity-Skills REST** | HTTP | `http://127.0.0.1:8090/` | `~/.agents/skills/unity-skills/` or `.omp/skills/` |
| **unity-cli** | stdio | Process spawn (`unity mcp`) | `.omp/mcp.json` |
| **unityMCP** (optional) | HTTP | `http://127.0.0.1:8080/mcp` | `.omp/mcp.json` (requires separate MCPForUnity server running) |
