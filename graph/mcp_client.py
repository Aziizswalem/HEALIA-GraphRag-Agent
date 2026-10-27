"""Minimal JSON-RPC client for the remote Neo4j MCP server."""
from __future__ import annotations

import json
import itertools
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from config.settings import get_settings

_ids = itertools.count(1)


class MCPError(RuntimeError):
    """Raised when the MCP server returns an error response."""


def _headers() -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    auth = settings.MCP_AUTHORIZATION.strip()
    if auth:
        headers["Authorization"] = auth
    return headers


def _rpc(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    if getattr(settings, "DEMO_MODE", False):
        return {}
    payload = {
        "jsonrpc": "2.0",
        "id": next(_ids),
        "method": method,
        "params": params or {},
    }
    request = Request(
        settings.MCP_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=float(settings.MCP_TIMEOUT_SECONDS)) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise MCPError(f"MCP HTTP {exc.code}: {detail}") from exc

    data = json.loads(raw)
    if "error" in data:
        raise MCPError(str(data["error"]))
    result = data.get("result")
    if not isinstance(result, dict):
        raise MCPError("Invalid MCP response: missing object result")
    return result


def _tool_text(result: dict[str, Any]) -> str:
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    chunks = [
        str(item.get("text", ""))
        for item in content
        if isinstance(item, dict) and item.get("type") == "text"
    ]
    return "\n".join(chunk for chunk in chunks if chunk)


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> str:
    result = _rpc(
        "tools/call",
        {"name": name, "arguments": arguments or {}},
    )
    return _tool_text(result)


def get_schema_map() -> dict[str, Any]:
    """Return MCP get-schema output normalized to the apoc.meta.schema map shape."""
    text = call_tool("get-schema", {"properties": {}})
    if not text.strip():
        return {}
    raw = json.loads(text)
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, list):
        return {}
    out: dict[str, Any] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        value = item.get("value")
        if isinstance(key, str) and isinstance(value, dict):
            out[key] = value
    return out


def read_cypher(cypher: str) -> list[dict[str, Any]]:
    text = call_tool("read-cypher", {"query": cypher})
    if not text.strip():
        return []
    data = json.loads(text)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []
