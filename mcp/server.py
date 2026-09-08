#!/usr/bin/env python3
"""
Unity-Skills MCP Server
Connects Oh My Pi and any MCP client directly to the Unity-Skills REST API (ports 8090-8100).
"""

import os
import sys
import json
import time
from typing import Any, Dict, List, Optional
import httpx
from fastmcp import FastMCP

PORT_RANGE_START = 8090
PORT_RANGE_END = 8100
DEFAULT_TIMEOUT = 120.0
HEALTH_TIMEOUT = 1.5

mcp = FastMCP("unity-skills")

def _load_registry() -> Dict[str, Any]:
    reg_path = os.path.join(os.path.expanduser("~"), ".unity_skills", "registry.json")
    if os.path.isfile(reg_path):
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def _find_unity_base_url() -> Optional[str]:
    # 1. Environment variable override
    env_url = os.environ.get("UNITY_SKILLS_URL")
    if env_url:
        return env_url.rstrip("/")

    # 2. Check registry for active instance
    registry = _load_registry()
    now = time.time()
    for _, info in registry.items():
        if isinstance(info, dict):
            port = info.get("port")
            last_active = info.get("last_active")
            if isinstance(port, int) and (last_active is None or (now - last_active) < 120):
                url = f"http://localhost:{port}"
                try:
                    with httpx.Client(timeout=HEALTH_TIMEOUT) as client:
                        resp = client.get(f"{url}/health")
                        if resp.status_code == 200:
                            return url
                except Exception:
                    pass

    # 3. Scan default ports 8090-8100
    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        url = f"http://localhost:{port}"
        try:
            with httpx.Client(timeout=HEALTH_TIMEOUT) as client:
                resp = client.get(f"{url}/health")
                if resp.status_code == 200:
                    return url
        except Exception:
            pass

    return None

def _make_request(method: str, path: str, params: Optional[Dict[str, Any]] = None, json_body: Optional[Any] = None, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    base_url = _find_unity_base_url()
    if not base_url:
        return {
            "status": "error",
            "error": f"Unity Editor is not connected or Unity-Skills REST service is not running (scanned ports {PORT_RANGE_START}-{PORT_RANGE_END}). Open your project in Unity Editor and ensure UnitySkills is active."
        }

    url = f"{base_url}{path}"
    headers = {
        "User-Agent": "unity-skills-mcp/1.0",
        "X-Agent-Id": "OhMyPi-MCP",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            if method.upper() == "GET":
                resp = client.get(url, params=params, headers=headers)
            elif method.upper() == "POST":
                resp = client.post(url, json=json_body or {}, params=params, headers=headers)
            else:
                return {"status": "error", "error": f"Unsupported HTTP method: {method}"}

            try:
                return resp.json()
            except Exception:
                return {
                    "status": "success" if resp.status_code == 200 else "error",
                    "statusCode": resp.status_code,
                    "text": resp.text
                }
    except httpx.ConnectError:
        return {"status": "error", "error": f"Connection refused at {url}. Unity Editor may have closed or crashed."}
    except httpx.TimeoutException:
        return {"status": "error", "error": f"Request timed out after {timeout}s while communicating with Unity Editor."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_editor_health() -> Dict[str, Any]:
    """Check Unity Editor connection status and health.
    Returns project name, Unity version, scene name, compilation status, and operating mode.
    """
    return _make_request("GET", "/health", timeout=3.0)

@mcp.tool()
def search_skills(intent: str, top_n: int = 10) -> Dict[str, Any]:
    """Find and recommend the best Unity skills for an intent or task.
    Args:
        intent: Natural language description of what you want to do (e.g. 'create material', 'find camera', 'add rigidbody').
        top_n: Number of recommendations to return (default 10).
    """
    return _make_request("GET", "/skills/recommend", params={"intent": intent, "top_n": top_n})

@mcp.tool()
def get_skill_schema(category: Optional[str] = None) -> Dict[str, Any]:
    """Get the full schema definition and parameter signatures for Unity skills.
    Args:
        category: Optional category filter (e.g. 'gameobject', 'component', 'scene', 'material', 'physics').
    """
    params = {}
    if category:
        params["category"] = category
    return _make_request("GET", "/skills/schema", params=params)

@mcp.tool()
def execute_skill(skill_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a Unity skill operation in the active Unity Editor.
    Args:
        skill_name: Name of the skill to execute (e.g. 'create_gameobject', 'find_gameobjects', 'set_component_property').
        args: Dictionary of arguments for the skill.
    """
    return _make_request("POST", f"/skill/{skill_name}", json_body=args or {})

@mcp.tool()
def dry_run_skill(skill_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate and preview a Unity skill operation without applying changes.
    Args:
        skill_name: Name of the skill to dry run.
        args: Dictionary of arguments to validate.
    """
    return _make_request("POST", f"/skill/{skill_name}", params={"mode": "dryRun"}, json_body=args or {})

@mcp.tool()
def batch_skills(steps: List[Dict[str, Any]], continue_on_error: bool = False) -> Dict[str, Any]:
    """Execute multiple Unity skill operations in sequence.
    Args:
        steps: List of step dictionaries, each containing 'skill' (str) and 'args' (dict).
        continue_on_error: Whether to continue executing subsequent steps if one fails.
    """
    payload = {
        "steps": steps,
        "continueOnError": continue_on_error
    }
    return _make_request("POST", "/skills/batch", json_body=payload)

@mcp.tool()
def diagnose_editor(error_limit: int = 20, include_warnings: bool = True) -> Dict[str, Any]:
    """Get diagnostic information from Unity Editor including console errors, warnings, and compilation status.
    Args:
        error_limit: Max number of console errors to return.
        include_warnings: Include console warnings in diagnostic report.
    """
    return _make_request("GET", "/diagnose", params={
        "error_limit": error_limit,
        "include_warnings": include_warnings
    })

def main():
    mcp.run()

if __name__ == "__main__":
    main()
