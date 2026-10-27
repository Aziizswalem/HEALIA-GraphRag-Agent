"""
graph/schema/topology.py — v2

SOURCE UNIQUE DE TOPOLOGIE (fixes C2, C3)
──────────────────────────────────────────
Ce module est la seule source de topologie autorisée dans tout le pipeline.

AVANT :
  - topology.py (apoc.meta.schema via schema_manager) → cache TTL thread-safe
  - query_guard_patch.py (db.schema.visualization) → cache global sans TTL

Les deux caches pouvaient se désynchroniser et retourner des topologies
différentes. Sur cold start, les deux faisaient un appel réseau séquentiel.

APRÈS :
  - Seul get_topology_cached_or_fetch() de ce module est utilisé.
  - query_guard_patch.get_dynamic_topology() supprimé.
  - cypher_generator, cypher_validator et graph_path_semantic_check
    utilisent tous la même variable domain_topology issue de ce module.
  - Sur warm cache (TTL non expiré) : 0 appel réseau, ~0ms de surcoût.

POLITIQUE DE FALLBACK :
  Si live introspection échoue ou retourne 0 relations →
  fallback sur FULL_SCHEMA statique (static_schema.py), vérifié
  contre la base live en 2026-05.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from config.settings import get_settings
from graph.schema.schema_manager import get_full_schema_cached_or_fetch
from graph.schema.static_schema import FULL_SCHEMA

logger = logging.getLogger(__name__)

_topology_lock = threading.Lock()
_topology_cache: tuple[float, str, int, str] | None = None


def _safe_name(value: Any) -> str:
    text = str(value or "").strip().strip("`")
    if not text:
        return ""
    if not text.replace("_", "").isalnum():
        return ""
    if not (text[0].isalpha() or text[0] == "_"):
        return ""
    return text


def _triples_from_meta_map(meta_map: dict[str, Any]) -> set[tuple[str, str, str]]:
    triples: set[tuple[str, str, str]] = set()
    for label, details in (meta_map or {}).items():
        source_or_target = _safe_name(label)
        if not source_or_target or not isinstance(details, dict):
            continue
        if details.get("type") != "node":
            continue
        relationships = details.get("relationships", {})
        if not isinstance(relationships, dict):
            continue
        for rel_type, rel_info in relationships.items():
            rel_name = _safe_name(rel_type)
            if not rel_name or not isinstance(rel_info, dict):
                continue
            targets = rel_info.get("labels", [])
            if not isinstance(targets, list):
                continue
            direction = str(rel_info.get("direction") or "out").lower()
            for target in targets:
                other = _safe_name(target)
                if not other:
                    continue
                if direction == "in":
                    triples.add((other, rel_name, source_or_target))
                else:
                    triples.add((source_or_target, rel_name, other))
    return triples


def format_topology(triples: set[tuple[str, str, str]]) -> str:
    lines = [
        "DYNAMIC GRAPH TOPOLOGY (live Neo4j schema)",
        "Use these relationship directions for graph path validation.",
        "",
    ]
    for source, rel_type, target in sorted(triples):
        lines.append(f"(:{source})-[:{rel_type}]->(:{target})")
    return "\n".join(lines)


def fetch_dynamic_topology() -> tuple[str, int]:
    """Fetch live topology from the cached schema map and format it for the path guard."""
    meta_map = get_full_schema_cached_or_fetch()
    triples = _triples_from_meta_map(meta_map)
    return format_topology(triples), len(triples)


def get_topology_cached_or_fetch() -> tuple[str, int, str]:
    """
    Return (topology_text, triple_count, source).

    SOURCE UNIQUE — utilisée par :
      - cypher_generator.py  (_build_full_schema)
      - cypher_validator.py  (construction de full_schema + passage à graph_path_semantic_check)

    Cache TTL thread-safe (SCHEMA_CACHE_TTL_SECONDS).
    Sur warm cache : 0 appel réseau → latence ~0ms.
    Sur cold start : 1 seul appel réseau (apoc.meta.schema via schema_manager).

    Fallback : si live introspection échoue ou retourne 0 relations,
    on utilise FULL_SCHEMA (static_schema.py) comme source de vérité.
    """
    global _topology_cache

    ttl = float(get_settings().SCHEMA_CACHE_TTL_SECONDS)
    now = time.monotonic()
    with _topology_lock:
        if _topology_cache is not None:
            ts, topology, count, source = _topology_cache
            if now - ts < ttl:
                return topology, count, source

    source = "dynamic"
    if getattr(get_settings(), "DEMO_MODE", False):
        return FULL_SCHEMA, 0, "demo_mode"
    try:
        topology, count = fetch_dynamic_topology()
        if count <= 0:
            raise RuntimeError("dynamic topology returned no relationships")
    except Exception as exc:
        logger.warning("dynamic topology unavailable, using FULL_SCHEMA fallback: %s", exc)
        topology = FULL_SCHEMA
        count = 0
        source = "static_fallback"

    with _topology_lock:
        _topology_cache = (time.monotonic(), topology, count, source)
    return topology, count, source


def clear_topology_cache() -> None:
    """Force un rechargement au prochain appel (utile après migration de schéma)."""
    global _topology_cache
    with _topology_lock:
        _topology_cache = None
