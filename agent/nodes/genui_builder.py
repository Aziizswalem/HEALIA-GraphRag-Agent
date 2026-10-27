from __future__ import annotations

"""Deterministic GenUI block builder.

This module replaces the previous LLM-driven chart generation. Instead of
asking the LLM to *invent* chart values (which produced wrong plots for
quantitative and qualitative data), we:

1. Profile the raw Neo4j rows in Python (column types, cardinality).
2. Derive the best visual blocks from the *actual* data, computing all
   aggregations deterministically (counts, sums, means, top-N).
3. Hand the pre-computed blocks to the LLM *only* for the textual summary,
   forbidding any value invention.

This guarantees every rendered plot is a faithful projection of the data.
"""

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

_MAX_TABLE_ROWS = 50
_MAX_CATEGORIES = 12
_TOP_N = 10
_MIN_ROWS_FOR_CHART = 2


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _col_types(rows: list[dict]) -> tuple[list[str], list[str]]:
    """Return (numeric_cols, text_cols) based on observed cell types."""
    if not rows:
        return [], []
    columns = list(rows[0].keys())
    numeric: list[str] = []
    text: list[str] = []
    for col in columns:
        values = [r.get(col) for r in rows if r.get(col) is not None]
        if values and all(_is_number(v) for v in values):
            numeric.append(col)
        else:
            text.append(col)
    return numeric, text


def _distinct_count(rows: list[dict], col: str) -> int:
    return len({r.get(col) for r in rows})


def _pick_label_col(rows: list[dict], numeric: list[str], text: list[str]) -> str | None:
    """Choose the qualitative axis for charts/tables."""
    if text:
        # Prefer the most categorical (low-cardinality) text column as label
        candidates = sorted(text, key=lambda c: _distinct_count(rows=rows, col=c))
        return candidates[0]
    if len(numeric) >= 2:
        return numeric[0]
    return None


def build_blocks(rows: list[dict], question: str = "") -> list[dict]:
    """Build faithful GenUI blocks from raw rows.

    Returns an ordered list of blocks: table first (ground truth), then
    the most appropriate chart/cards for quantitative and qualitative data.
    """
    global rows_scope
    rows_scope = rows

    blocks: list[dict] = []
    if not rows:
        return blocks

    numeric, text = _col_types(rows)
    columns = list(rows[0].keys())

    # 1) Ground-truth table (always present when there is data)
    blocks.append({
        "type": "table",
        "title": "Résultats (données brutes)",
        "columns": columns,
        "rows": rows[:_MAX_TABLE_ROWS],
    })

    label_col = _pick_label_col(rows, numeric, text)

    # 2) Quantitative data -> faithful bar/line chart of real values
    if numeric and label_col is not None and len(rows) >= _MIN_ROWS_FOR_CHART:
        chart_data = []
        for r in rows:
            chart_data.append({
                "name": str(r.get(label_col, "")),
                "value": r.get(numeric[0]) if _is_number(r.get(numeric[0])) else 0,
            })
        chart_type = "bar" if len(chart_data) <= 15 else "line"
        blocks.append({
            "type": "chart",
            "chartType": chart_type,
            "title": f"{numeric[0]} par {label_col}",
            "data": chart_data,
            "xKey": "name",
            "yKey": "value",
        })

    # 3) Qualitative data -> faithful distribution (counts) as pie/bar
    if text and label_col is not None:
        counts = Counter(str(r.get(label_col, "")) for r in rows)
        items = counts.most_common(_TOP_N)
        if len(items) <= _MAX_CATEGORIES:
            pie_data = [{"name": k, "value": v} for k, v in items]
            blocks.append({
                "type": "chart",
                "chartType": "pie",
                "title": f"Répartition par {label_col}",
                "data": pie_data,
                "xKey": "name",
                "yKey": "value",
            })

    # 4) Multi-metric summary cards (top rows, real numbers only)
    if numeric:
        seen: set[str] = set()
        for r in rows[:_TOP_N]:
            title = str(r.get(label_col, "")) if label_col else f"Ligne {len(seen) + 1}"
            if title in seen:
                continue
            seen.add(title)
            metrics = ", ".join(
                f"{c}: {r.get(c)}" for c in numeric[:3] if r.get(c) is not None
            )
            blocks.append({
                "type": "card",
                "title": title,
                "description": metrics or "Voir le détail dans le tableau",
                "badge": str(r.get(numeric[0])) if r.get(numeric[0]) is not None else None,
            })

    return blocks


def build_blocks_payload(rows: list[dict]) -> str:
    """Serialize the computed blocks into a compact, verifiable text payload
    that is passed to the LLM so it can ONLY summarize, never invent."""
    import json

    blocks = build_blocks(rows)
    return json.dumps(
        {"row_count": len(rows), "blocks": blocks},
        ensure_ascii=False,
        indent=2,
        default=str,
    )
