"""
Extract usable property *keys* from `apoc.meta.schema()` so Cypher generation
can bind real variables (e.g. n.id, b.date).

APOC versions differ:
- Some expose ``existence`` as a **population fraction** in [0, 1] — we can
  drop keys with fraction 0 when SCHEMA_PROPERTY_MIN_EXISTENCE is 0.
- Neo4j 5 / recent APOC often use ``existence`` as a **boolean** meaning
  *existence constraint present* — **not** "fraction of nodes". Those must
  **not** be cast to 0.0 or every property disappears from the prompt.

We only treat ``existence`` as a usage fraction when it is numeric and not a
bool. Booleans are ignored for filtering.
"""
from __future__ import annotations

import re
from typing import Any

from config.settings import get_settings


def _usage_fraction(meta: Any) -> float | None:
    """Return a numeric 0..1 usage fraction if present; else None (do not filter)."""
    if not isinstance(meta, dict):
        return None
    raw = meta.get("existence")
    if raw is None:
        return None
    # Constraint flag in recent APOC — not a population statistic
    if isinstance(raw, bool):
        return None
    if isinstance(raw, str) and raw.lower() in ("true", "false"):
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    # Heuristic: fractions are in [0, 1]; large numbers are not usage ratios
    if v > 1.0:
        return None
    return v


def used_property_keys(
    entry: dict[str, Any],
    *,
    min_existence: float | None = None,
    max_keys: int | None = None,
) -> list[str]:
    """
    Ordered unique property names for one node or relationship entry from apoc.meta.schema.
    Excludes keys that are known unused (existence == 0) and optional Neo4j-internal names.
    """
    if min_existence is None or max_keys is None:
        s = get_settings()
        if min_existence is None:
            min_existence = float(s.SCHEMA_PROPERTY_MIN_EXISTENCE)
        if max_keys is None:
            max_keys = int(s.SCHEMA_MAX_PROPERTIES_PER_ENTITY)

    props = entry.get("properties")
    if not isinstance(props, dict) or not props:
        return []

    def raw_names() -> list[str]:
        return [
            n
            for n in sorted(props.keys())
            if isinstance(n, str) and not n.startswith("__")
        ]

    out: list[str] = []
    for name in raw_names():
        meta = props.get(name)
        ex = _usage_fraction(meta) if isinstance(meta, dict) else None
        if ex is not None:
            if min_existence > 0:
                if ex < min_existence:
                    continue
            elif ex <= 0:
                continue
        out.append(name)
        if len(out) >= max_keys:
            break

    # If APOC only provided boolean/non-numeric existence flags, nothing was filtered;
    # if we still got an empty list but keys exist, expose all raw keys (cap applied).
    if not out and raw_names():
        return raw_names()[:max_keys]
    return out


def used_property_info(
    entry: dict[str, Any],
    *,
    min_existence: float | None = None,
    max_keys: int | None = None,
) -> list[tuple[str, str]]:
    """Same filtering as *used_property_keys* but returns *(name, type)* tuples.

    The type is read from the ``"type"`` field of each property's entry in
    ``apoc.meta.schema()``.  Falls back to ``"?"`` when missing.
    """
    if min_existence is None or max_keys is None:
        s = get_settings()
        if min_existence is None:
            min_existence = float(s.SCHEMA_PROPERTY_MIN_EXISTENCE)
        if max_keys is None:
            max_keys = int(s.SCHEMA_MAX_PROPERTIES_PER_ENTITY)

    props = entry.get("properties")
    if not isinstance(props, dict) or not props:
        return []

    out: list[tuple[str, str]] = []
    for name in sorted(props.keys()):
        if not isinstance(name, str) or name.startswith("__"):
            continue
        meta = props.get(name)
        ex = _usage_fraction(meta) if isinstance(meta, dict) else None
        if ex is not None:
            if min_existence > 0:
                if ex < min_existence:
                    continue
            elif ex <= 0:
                continue
        ptype = str(meta.get("type", "?")) if isinstance(meta, dict) else "?"
        out.append((name, ptype))
        if len(out) >= max_keys:
            break
    if not out and props:
        for name in sorted(props.keys()):
            if isinstance(name, str) and not name.startswith("__"):
                meta = props.get(name)
                ptype = str(meta.get("type", "?")) if isinstance(meta, dict) else "?"
                out.append((name, ptype))
                if len(out) >= max_keys:
                    break
    return out


def props_bracket(names: list[str], *, max_in_bracket: int | None = None) -> str:
    """Return `` {a, b, c} `` for schema hints, or empty string if no keys."""
    if not names:
        return ""
    if max_in_bracket is None:
        max_in_bracket = int(get_settings().SCHEMA_MAX_PROPERTIES_IN_PATTERN)
    show = names[:max_in_bracket]
    tail = len(names) - len(show)
    inner = ", ".join(show)
    if tail > 0:
        inner += f", ... (+{tail} more)"
    return f" {{{inner}}}"


def format_node_pattern(meta_map: dict[str, Any], label: str) -> str:
    details = meta_map.get(label)
    if not isinstance(details, dict) or details.get("type") != "node":
        return f":{label}"
    keys = used_property_keys(details)
    return f":{label}{props_bracket(keys)}"


def format_node_line(meta_map: dict[str, Any], label: str) -> str:
    """Single node pattern for prompts, e.g. ``(:Patient {id, nom})``."""
    return f"({format_node_pattern(meta_map, label)})"


def _token_match(name: str, tokens: set[str]) -> bool:
    """Check if any normalized token from `name` is in `tokens`."""
    raw = re.sub(r"[:/\\\-]+", " ", name).lower()
    name_tokens = {t for t in re.findall(r"[a-z0-9]+", raw) if len(t) > 2}
    return bool(name_tokens & tokens)


def format_enriched_schema(
    meta_map: dict[str, Any],
    selected_labels: list[str],
    *,
    question_tokens: set[str] | None = None,
    max_labels: int = 20,
    max_rels_per_label: int = 6,
    max_unfiltered_rels_per_label: int = 2,
    show_properties: bool = True,
) -> str:
    """Grouped schema: for each label, show properties + relevant relationships.

    When *question_tokens* is provided, only relationships whose type or target
    label matches the question tokens are shown.  Unfiltered relationships are
    collapsed to a short summary to keep the prompt small.

    Set *show_properties=False* to skip the ``Properties: ...`` line (e.g.
    when ``format_property_registry()`` is injected separately by the
    Cypher generator to provide richer semantic annotations).
    """
    lines: list[str] = ["## Schema context (grouped by node label)"]
    label_set = set(selected_labels[:max_labels])

    for label in sorted(label_set):
        details = meta_map.get(label)
        if not isinstance(details, dict) or details.get("type") != "node":
            continue

        lines.append(f"\n### {label}")
        if show_properties:
            props = used_property_info(details)
            if props:
                lines.append(f"  Properties: {', '.join(f'{k}: {t}' for k, t in props)}")
            else:
                lines.append("  Properties: (none)")

        relationships = details.get("relationships", {})
        if not isinstance(relationships, dict) or not relationships:
            lines.append("  Relationships: (none)")
            continue

        outgoing: list[str] = []
        incoming: list[str] = []
        total_out = 0
        total_in = 0

        for rel_type, rel_info in relationships.items():
            if not isinstance(rel_info, dict):
                continue
            targets = rel_info.get("labels", [])
            if not isinstance(targets, list):
                continue
            direction = str(rel_info.get("direction") or "out").lower()
            rkeys = used_property_keys(rel_info)
            rprops = props_bracket(rkeys)
            for tgt in targets:
                if not isinstance(tgt, str):
                    continue
                if direction == "in":
                    total_in += 1
                else:
                    total_out += 1
                if question_tokens and not (
                    _token_match(rel_type, question_tokens)
                    or _token_match(tgt, question_tokens)
                ):
                    continue
                if direction == "in":
                    incoming.append(f"(:{tgt})-[:{rel_type}{rprops}]->")
                else:
                    outgoing.append(f"-[:{rel_type}{rprops}]->(:{tgt})")

        shown = 0
        for pattern in outgoing[:max_rels_per_label]:
            lines.append(f"  {pattern}")
            shown += 1
        for pattern in incoming[:max_rels_per_label]:
            lines.append(f"  {pattern} (incoming)")
            shown += 1

        if shown == 0:
            total = total_out + total_in
            if total > 0:
                # Show a few unfiltered so the LLM still sees available paths
                unfiltered = 0
                for rel_type, rel_info in relationships.items():
                    if not isinstance(rel_info, dict):
                        continue
                    for tgt in (rel_info.get("labels") or []):
                        if not isinstance(tgt, str):
                            continue
                        if unfiltered >= max_unfiltered_rels_per_label:
                            break
                        direction = str(rel_info.get("direction") or "out").lower()
                        rkeys = used_property_keys(rel_info)
                        rprops = props_bracket(rkeys)
                        if direction == "in":
                            lines.append(f"  (:{tgt})-[:{rel_type}{rprops}]-> (incoming)")
                        else:
                            lines.append(f"  -[:{rel_type}{rprops}]->(:{tgt})")
                        unfiltered += 1
                if total > unfiltered:
                    lines.append(f"  (… {total - unfiltered} other relationship types)")
            else:
                lines.append("  Relationships: (none)")

    return "\n".join(lines)


def format_rel_pattern(
    meta_map: dict[str, Any],
    source_label: str,
    rel_type: str,
    rel_info: dict[str, Any],
    target_label: str,
) -> str:
    left = format_node_pattern(meta_map, source_label)
    right = format_node_pattern(meta_map, target_label)
    rkeys = used_property_keys(rel_info)
    mid = f":{rel_type}{props_bracket(rkeys)}"
    return f"({left})-[{mid}]->({right})"


def properties_lines_for_labels(
    meta_map: dict[str, Any],
    labels: list[str],
    *,
    max_labels: int = 24,
) -> list[str]:
    """Human-readable lines: ``  :Label → prop1: type, prop2: type `` for prompts."""
    lines: list[str] = []
    for label in labels[:max_labels]:
        details = meta_map.get(label)
        if not isinstance(details, dict) or details.get("type") != "node":
            continue
        props = used_property_info(details)
        if not props:
            continue
        lines.append(f"  :{label} → {', '.join(f'{k}: {t}' for k, t in props)}")
    return lines
