"""
guardrails/_common.py — Shared Cypher validation patterns and helpers.

Extracted from query_guard.py and query_guard_patch.py to eliminate
duplicated regex patterns and utility functions across both files.

See also:
  - guardrails/query_guard.py          (v1 guardrails)
  - guardrails/query_guard_patch.py    (v2 guardrails — FIX C5, C6)
"""
from __future__ import annotations

import re
from typing import Set, Tuple

# ── Shared regex patterns ─────────────────────────────────────────────────────

NODE_PATTERN_RE = re.compile(r"\([^)]*\)")
REL_PATTERN_RE = re.compile(r"\[[^\]]*\]")
SCHEMA_LABEL_RE = re.compile(r"\(\s*:([A-Za-z_][A-Za-z0-9_]*)")
SCHEMA_REL_RE = re.compile(r"\[\s*:([A-Za-z_][A-Za-z0-9_]*)")
SCHEMA_PROP_RE = re.compile(r"\{([^{}]+)\}")
QUERY_PROP_ACCESS_RE = re.compile(r"\.\s*`?([A-Za-z_][A-Za-z0-9_]*)`?\b")

# System temporal accessors (date().year, datetime().month, etc.)
# These are built-in Cypher functions, not domain properties.
SYSTEM_TEMPORAL_ACCESSORS: Set[str] = {
    "year", "month", "day", "hour", "minute", "second",
    "week", "quarter", "ordinalday", "timezone", "offset",
}


# ── Shared utility functions ──────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Collapse all whitespace and lowercase."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_query_labels(cypher: str) -> Set[str]:
    """Extract all node labels referenced in a Cypher query."""
    labels: Set[str] = set()
    for pattern in NODE_PATTERN_RE.findall(cypher or ""):
        head = pattern.split("{", 1)[0]
        labels.update(re.findall(r":\s*`?([A-Za-z_][A-Za-z0-9_]*)`?", head))
    return labels


def extract_query_relationships(cypher: str) -> Set[str]:
    """Extract all relationship types referenced in a Cypher query."""
    rels: Set[str] = set()
    for pattern in REL_PATTERN_RE.findall(cypher or ""):
        head = pattern.split("{", 1)[0]
        rels.update(
            re.findall(r"(?:(?<=:)|(?<=\|))\s*`?([A-Za-z_][A-Za-z0-9_]*)`?", head)
        )
    return rels


def extract_query_pattern_map_properties(cypher: str) -> Set[str]:
    """Extract property names used inside curly-brace map literals in patterns."""
    props: Set[str] = set()
    for pattern in [*NODE_PATTERN_RE.findall(cypher or ""), *REL_PATTERN_RE.findall(cypher or "")]:
        if "{" not in pattern:
            continue
        _, _, tail = pattern.partition("{")
        block, _, _ = tail.partition("}")
        props.update(
            match.group(1)
            for match in re.finditer(r"`?([A-Za-z_][A-Za-z0-9_]*)`?\s*:", block)
        )
    return props


def format_unknown_names(values: Set[str]) -> str:
    """Format a set of unknown names for error messages."""
    return ", ".join(f"`{value}`" for value in sorted(values))


def extract_schema_names(schema_context: str) -> Tuple[Set[str], Set[str], Set[str]]:
    """Extract labels, relationship types, and properties from a schema context string.

    Returns (labels, relationships, properties) preserving the original case
    from the schema text.  Does NOT enrich with static schema — use the
    ``query_guard_patch`` variant when static enrichment is needed.
    """
    text = schema_context or ""
    labels = set(SCHEMA_LABEL_RE.findall(text))
    relationships = set(SCHEMA_REL_RE.findall(text))
    properties: Set[str] = set()
    for block in SCHEMA_PROP_RE.findall(text):
        for raw_name in block.split(","):
            candidate = raw_name.strip()
            if not candidate or candidate.startswith("..."):
                continue
            match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", candidate)
            if match:
                properties.add(match.group(1))
    return labels, relationships, properties


def schema_is_available(schema_context: str) -> bool:
    """Check whether a meaningful schema is present (vs. an error placeholder)."""
    _SCHEMA_UNAVAILABLE_HINTS: Tuple[str, ...] = (
        "schema unavailable",
        "dynamic neo4j schema discovery failed",
    )
    normalized = normalize_text(schema_context)
    if not normalized:
        return False
    if any(hint in normalized for hint in _SCHEMA_UNAVAILABLE_HINTS):
        return False
    return "(:" in normalized
