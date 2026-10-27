"""
Sample distinct property values from Neo4j for labels/properties you configure.
Injected into the Cypher system prompt so the LLM maps user language ("radio")
to real DB values ("radiologie") without maintaining per-query few-shots.

Configure via SCHEMA_ENUM_HINTS JSON, e.g.
  {"ActeMedical": ["type"], "Patient": ["chronic_disease"]}
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any

from config.settings import get_settings

_enum_memory: dict[str, tuple[float, dict[str, list[Any]]]] = {}


def clear_enum_memory() -> None:
    """Call when schema cache is invalidated (e.g. admin refresh)."""
    _enum_memory.clear()


def _safe_cypher_ident(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name))


def _parse_enum_hints() -> list[tuple[str, str]]:
    s = get_settings()
    raw = (s.SCHEMA_ENUM_HINTS or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    out: list[tuple[str, str]] = []
    for label, props in data.items():
        if not isinstance(label, str) or not _safe_cypher_ident(label):
            continue
        if isinstance(props, str):
            props = [props]
        if not isinstance(props, list):
            continue
        for p in props:
            if isinstance(p, str) and _safe_cypher_ident(p):
                out.append((label, p))
    return out


def _enum_cache_key(uri: str) -> str:
    s = get_settings()
    h = hashlib.sha1(uri.encode("utf-8")).hexdigest()[:12]
    return f"{s.SCHEMA_CACHE_PREFIX}:enums:{s.SCHEMA_VERSION}:{h}"


def _fetch_distinct_values(label: str, prop: str, limit: int) -> list[Any]:
    if not _safe_cypher_ident(label) or not _safe_cypher_ident(prop):
        return []
    cypher = (
        f"MATCH (n:`{label}`) WHERE n.`{prop}` IS NOT NULL "
        f"RETURN DISTINCT n.`{prop}` AS v LIMIT {int(limit)}"
    )
    out: list[Any] = []
    settings = get_settings()
    if getattr(settings, "mcp_enabled", lambda: False)():
        try:
            from graph.mcp_client import read_cypher

            return [rec.get("v") for rec in read_cypher(cypher) if rec.get("v") is not None]
        except Exception:
            return []

    from graph.client import get_driver

    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run(cypher)
            for rec in result:
                v = rec.get("v")
                out.append(v)
    except Exception:
        return []
    return out


def _serialize_val(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).strip()
    return s[:200]


def load_enum_value_map() -> dict[str, list[str]]:
    """
    Returns e.g. {"ActeMedical.type": ["radiologie", "labo", ...]} (stringified values).
    Cached with same TTL as schema cache.
    """
    s = get_settings()
    pairs = _parse_enum_hints()
    if not pairs:
        return {}

    uri = s.MCP_URL if getattr(s, "mcp_enabled", lambda: False)() else s.NEO4J_URI
    cache_key = _enum_cache_key(uri)
    now = time.time()
    ttl = s.SCHEMA_CACHE_TTL_SECONDS
    limit = int(s.SCHEMA_ENUM_VALUE_LIMIT)

    cached = _enum_memory.get(cache_key)
    if cached and now - cached[0] < ttl:
        return cached[1]

    blob: dict[str, list[str]] = {}
    for label, prop in pairs:
        key = f"{label}.{prop}"
        raw_vals = _fetch_distinct_values(label, prop, limit)
        blob[key] = [_serialize_val(v) for v in raw_vals]

    _enum_memory[cache_key] = (now, blob)

    return blob


def format_enum_hints_block() -> str:
    """Markdown block appended to AVAILABLE SCHEMA for the Cypher LLM."""
    m = load_enum_value_map()
    if not m:
        return ""
    lines = [
        "",
        "KNOWN VALUES SAMPLED FROM DATABASE (use these literals or partial match; do not invent values):",
    ]
    for k in sorted(m.keys()):
        vals = m[k]
        if not vals:
            lines.append(f"  {k}: (no distinct values returned — check property name or data)")
            continue
        shown = vals[:80]
        tail = len(vals) - len(shown)
        suffix = f" … (+{tail} more distinct values)" if tail > 0 else ""
        lines.append(f"  {k}: {', '.join(shown)}{suffix}")
    return "\n".join(lines)


def append_enum_hints_to_context(schema_context: str) -> str:
    block = format_enum_hints_block()
    if not block:
        return schema_context
    return schema_context.rstrip() + "\n" + block
