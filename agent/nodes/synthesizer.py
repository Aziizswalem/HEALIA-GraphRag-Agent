from __future__ import annotations

import json
import logging
from typing import Any, Iterator

from agent.state import AgentState
from agent.trace_util import step
from llm.prompts.synthesis_system import SYNTHESIS_SYSTEM_PROMPT
from llm.prompts.genui_summary_system import GENUI_SUMMARY_SYSTEM_PROMPT
from llm.router import get_provider

logger = logging.getLogger(__name__)

_SYNTHESIZER_MAX_ROWS = 30


def _build_payload(results: list[object]) -> tuple[str, int]:
    total = len(results)
    capped = results[:_SYNTHESIZER_MAX_ROWS]
    results_str = json.dumps(capped, ensure_ascii=False, indent=2, default=str)
    truncation_note = (
        f"\n(Resultats tronques : affichage de {len(capped)} sur {total})"
        if total > _SYNTHESIZER_MAX_ROWS
        else ""
    )
    data_payload = f"Data retrieved from the database:{truncation_note}\n{results_str}"
    return data_payload, total


def _build_trace_step(total_rows: int) -> dict:
    return step(
        "synthesizer",
        "answer_ready",
        results_in_prompt=min(100, total_rows),
        total_rows=total_rows,
    )


def _build_genui_trace_step(total_rows: int) -> dict:
    return step(
        "synthesizer",
        "genui_ready",
        results_in_prompt=min(100, total_rows),
        total_rows=total_rows,
    )


def finalize_streamed_answer(*, final_answer: str, total_rows: int) -> dict:
    return {
        "final_answer": final_answer,
        "trace_steps": [_build_trace_step(total_rows)],
    }


def stream(state: AgentState) -> tuple[Iterator[str], int]:
    provider = get_provider()
    results = state.get("graph_results", []) or []
    question = state["question"]
    data_payload, total = _build_payload(results)
    token_iter = provider.stream_synthesize_answer(
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        question=question,
        data_payload=data_payload,
    )
    return token_iter, total


def run(state: AgentState) -> dict:
    provider = get_provider()
    results = state.get("graph_results", []) or []
    question = state["question"]
    data_payload, total = _build_payload(results)
    try:
        final_answer = provider.synthesize_answer(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            question=question,
            data_payload=data_payload,
        )
    except Exception as exc:
        logger.warning("LLM unavailable (%s), returning raw results summary", exc)
        final_answer = f"{len(results)} résultat(s) trouvé(s) dans la base de données."
    return finalize_streamed_answer(final_answer=final_answer, total_rows=total)


def _auto_generate_blocks(results: list[dict], question: str) -> tuple[str, list[dict]]:
    """Generate GenUI blocks directly from raw Neo4j results when LLM is unavailable."""
    if not results:
        return "Aucun résultat trouvé dans la base de données.", []

    blocks: list[dict] = []
    columns = list(results[0].keys()) if results else []
    numeric_cols = [c for c in columns if any(isinstance(r.get(c), (int, float)) for r in results)]
    text_cols = [c for c in columns if c not in numeric_cols]

    answer = f"Voici les résultats de votre requête. {len(results)} ligne(s) trouvée(s)."

    table_block: dict = {
        "type": "table",
        "title": "Résultats bruts",
        "columns": columns,
        "rows": results,
    }
    blocks.append(table_block)

    if len(numeric_cols) >= 1 and len(results) >= 2:
        if text_cols:
            x_key = text_cols[0]
        else:
            x_key = columns[0]

        for num_col in numeric_cols[:2]:
            chart_data = []
            for r in results:
                point: dict = {"name": str(r.get(x_key, ""))}
                point[num_col] = r.get(num_col, 0)
                chart_data.append(point)

            chart_type = "bar" if len(results) < 15 else "line"
            blocks.append({
                "type": "chart",
                "chartType": chart_type,
                "title": f"Répartition par {x_key}",
                "data": chart_data,
                "xKey": "name",
                "yKey": num_col,
            })

    seen_titles: set[str] = set()
    for r in results[:6]:
        title = str(r.get(text_cols[0] if text_cols else columns[0], ""))
        if title in seen_titles:
            continue
        seen_titles.add(title)
        desc_parts = [f"{c}: {r.get(c, '')}" for c in numeric_cols[:3]]
        blocks.append({
            "type": "card",
            "title": title,
            "description": " | ".join(desc_parts) if desc_parts else "Voir les détails",
            "badge": str(r.get(numeric_cols[0], "")) if numeric_cols else None,
        })

    return answer, blocks


def run_genui(state: AgentState) -> dict:
    provider = get_provider()
    results = state.get("graph_results", []) or []
    question = state["question"]
    data_payload, total = _build_payload(results)

    answer = ""
    genui_blocks: list[dict[str, Any]] = []

    if not results:
        return {
            "final_answer": "Aucun résultat trouvé dans la base de données.",
            "genui_blocks": [],
            "trace_steps": [_build_trace_step(total), _build_genui_trace_step(total)],
        }

    # 1) Build faithful blocks deterministically from the raw rows.
    from agent.nodes.genui_builder import build_blocks, build_blocks_payload

    genui_blocks = build_blocks(results, question)

    # 2) Let the LLM ONLY write the textual summary from the computed blocks.
    #    It must never invent chart values (those come from build_blocks).
    try:
        answer = provider.synthesize_answer(
            system_prompt=GENUI_SUMMARY_SYSTEM_PROMPT,
            question=question,
            data_payload=build_blocks_payload(results),
        )
    except Exception as exc:
        logger.warning("LLM unavailable (%s), using deterministic summary", exc)
        answer = _auto_generate_blocks(results, question)[0]

    return {
        "final_answer": answer,
        "genui_blocks": genui_blocks,
        "trace_steps": [_build_trace_step(total), _build_genui_trace_step(total)],
    }
