#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# UnitySkills MCP bridge: exposes the REST skills as a small set of MCP tools over stdio, so MCP-aware
# agents (Claude Code, Cursor, Codex, ...) see Unity in their tool list without loading SKILL.md.
# Port discovery and retries stay in unity_skills.py (registry.json + 8090-8100 scan), so a port change
# after a domain reload is invisible to the agent.

# Grab the raw byte streams BEFORE importing unity_skills: on Windows that import rewraps sys.stdout.
import sys
_IN = sys.stdin.buffer
_OUT = sys.stdout.buffer
sys.stdout = sys.stderr  # stray prints must never corrupt the JSON-RPC stream

import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unity_skills as us  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "unity-skills", "version": getattr(us, "__version__", "0")}

INSTRUCTIONS = (
    "Controls the running Unity Editor through UnitySkills (800+ skills). Prefer these tools over editing "
    "scene/asset files by hand. Flow: unity_find_skills -> unity_skill_info (exact parameters) -> unity_call. "
    "Use unity_batch for several steps. Domain reloads make Unity briefly unreachable: retry, or call "
    "unity_status first."
)

TOOLS = [
    {
        "name": "unity_status",
        "description": "Health of the connected Unity Editor (port, project, mode, reloading/compiling) plus all "
                       "registered Unity instances. Call first when anything fails to connect.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "unity_find_skills",
        "description": "Keyword search over all Unity skills (name, description, category). Every term must match. "
                       "Returns name/category/description only; use unity_skill_info for parameters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Whitespace-separated keywords, e.g. 'create material'."},
                "category": {"type": "string", "description": "Optional exact category, e.g. 'GameObject'."},
                "limit": {"type": "integer", "description": "Max results (default 20)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "unity_skill_info",
        "description": "Exact parameter schema and metadata of one skill by name.",
        "inputSchema": {
            "type": "object",
            "properties": {"skill": {"type": "string", "description": "Skill name, e.g. 'gameobject_create'."}},
            "required": ["skill"],
        },
    },
    {
        "name": "unity_call",
        "description": "Run one Unity skill. 'params' are that skill's arguments (see unity_skill_info). Long-running "
                       "skills return a jobId; set wait_for_job to block until done.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "Skill name."},
                "params": {"type": "object", "description": "Skill arguments as a JSON object."},
                "wait_for_job": {"type": "boolean", "description": "Wait for a returned jobId to finish."},
                "dry_run_token": {"type": "string", "description": "Token from a dry run of the same arguments."},
            },
            "required": ["skill"],
        },
    },
    {
        "name": "unity_batch",
        "description": "Run several skills in one request. Each step is {\"skill\": name, \"args\": {...}}. "
                       "mode 'dryRun' validates without executing; 'transactional' is all-or-nothing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "steps": {"type": "array", "items": {"type": "object"}},
                "continue_on_error": {"type": "boolean"},
                "mode": {"type": "string", "enum": ["dryRun", "transactional"]},
                "diff": {"type": "boolean", "description": "Return the net scene diff on success."},
            },
            "required": ["steps"],
        },
    },
]


def _status():
    return {"server": us.get_server_status(), "instances": us.list_instances()}


def _find_skills(a):
    results = us.search_skills(a.get("query", ""), category=a.get("category"), limit=int(a.get("limit") or 20))
    if results and isinstance(results[0], dict) and results[0].get("status") == "error":
        return results[0], True
    return {"count": len(results), "skills": results}, False


def _skill_info(a):
    name = a.get("skill", "")
    schema = us.get_skill_schema()
    skills = schema.get("skills") if isinstance(schema, dict) else None
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict) and s.get("name") == name:
                return s, False
    elif isinstance(skills, dict) and name in skills:
        return skills[name], False
    # Not in the cached schema (or schema unavailable): fall back to the server-side recommender.
    return us.find_skills(name, top_n=3, include_schema=True), False


def _call(a):
    params = a.get("params") or {}
    if not isinstance(params, dict):
        return {"success": False, "error": "'params' must be an object"}, True
    client = us._get_default_client()
    result = client.call(a["skill"], wait_for_job=bool(a.get("wait_for_job")),
                         dry_run_token=a.get("dry_run_token"), **params)
    return result, isinstance(result, dict) and result.get("success") is False


def _batch(a):
    result = us.execute_batch(a.get("steps") or [], continue_on_error=a.get("continue_on_error"),
                              diff=bool(a.get("diff")), mode=a.get("mode"))
    failed = isinstance(result, dict) and (result.get("success") is False or result.get("status") == "error")
    return result, failed


def _run_tool(name, args):
    if name == "unity_status":
        return _status(), False
    if name == "unity_find_skills":
        return _find_skills(args)
    if name == "unity_skill_info":
        return _skill_info(args)
    if name == "unity_call":
        return _call(args)
    if name == "unity_batch":
        return _batch(args)
    return {"error": f"Unknown tool: {name}"}, True


def _send(msg):
    _OUT.write((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
    _OUT.flush()


def _reply(req_id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": req_id}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    _send(msg)


def _handle(msg):
    method = msg.get("method")
    req_id = msg.get("id")
    if req_id is None:  # notification (initialized, cancelled, ...): no reply
        return
    if method == "initialize":
        _reply(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS,
        })
    elif method == "ping":
        _reply(req_id, {})
    elif method == "tools/list":
        _reply(req_id, {"tools": TOOLS})
    elif method == "tools/call":
        p = msg.get("params") or {}
        try:
            data, is_error = _run_tool(p.get("name", ""), p.get("arguments") or {})
        except Exception as e:  # keep the bridge alive; surface the failure to the agent
            data, is_error = {"error": f"{type(e).__name__}: {e}"}, True
        _reply(req_id, {
            "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}],
            "isError": bool(is_error),
        })
    else:
        _reply(req_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main():
    for raw in _IN:
        line = raw.decode("utf-8-sig", "replace").strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            _reply(None, error={"code": -32700, "message": "Parse error"})
            continue
        if isinstance(msg, dict):
            _handle(msg)


if __name__ == "__main__":
    main()

# Producer:Betsy
