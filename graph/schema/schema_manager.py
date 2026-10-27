"""Schema manager — uses db.schema.visualization() + static overlay.

ROOT CAUSE FIX:
  apoc.meta.stats() silently skips relationships on high-cardinality nodes
  (BulletinSoin has 454K+ nodes). This caused [:AFFECTS] to be absent from
  the injected schema, making the LLM invent property-based lookups
  (MATCH (icc {assure_id: x})) that cause full scans and timeouts.

This module now exposes only the synchronous helpers used by the agent:
  - fetch_meta_schema()              — apoc.meta.schema() map (or MCP)
  - get_full_schema_cached_or_fetch() — thread-safe in-memory TTL cache
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_meta_cache_lock = threading.Lock()
_meta_cache_entry: tuple[float, dict[str, Any]] | None = None


def fetch_meta_schema() -> dict[str, Any]:
    """Synchronous ``apoc.meta.schema()`` map for agents and tools."""
    from config.settings import get_settings

    settings = get_settings()
    if getattr(settings, "DEMO_MODE", False):
        return {}
    if getattr(settings, "mcp_enabled", lambda: False)():
        try:
            from graph.mcp_client import get_schema_map

            return get_schema_map()
        except Exception as exc:
            logger.warning("fetch_meta_schema MCP: %s", exc)
            return {}

    from graph.client import get_driver

    cypher = """
        CALL apoc.meta.schema()
        YIELD value
        RETURN value
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            record = session.run(cypher).single()
            if not record or record["value"] is None:
                return {}
            raw = record["value"]
            return dict(raw) if isinstance(raw, dict) else {}
    except Exception as exc:
        logger.warning("fetch_meta_schema: %s", exc)
        return {}


def get_full_schema_cached_or_fetch() -> dict[str, Any]:
    """Thread-safe TTL cache around :func:`fetch_meta_schema` (see ``SCHEMA_CACHE_TTL_SECONDS``)."""
    from config.settings import get_settings

    global _meta_cache_entry

    ttl = float(get_settings().SCHEMA_CACHE_TTL_SECONDS)
    now = time.monotonic()
    with _meta_cache_lock:
        if _meta_cache_entry is not None:
            ts, cached = _meta_cache_entry
            if now - ts < ttl:
                return cached

    meta = fetch_meta_schema()
    with _meta_cache_lock:
        _meta_cache_entry = (time.monotonic(), meta)
        return meta
