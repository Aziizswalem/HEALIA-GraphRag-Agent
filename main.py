"""
Quick CLI to test the LangGraph agent loop.

Usage:
    python main.py
    python main.py "Quels actes medicaux a eu le patient 42 ?"

HTTP API (FastAPI):
    uvicorn api.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.graph import run_agent  # noqa: E402
from memory.conversation_buffer import append_turn, build_context_prompt  # noqa: E402
from memory.session_manager import ensure_session  # noqa: E402
from observability.langfuse_tracer import shutdown_langfuse  # noqa: E402


def _run_with_session(question: str, session_id: str) -> dict:
    agent_question = build_context_prompt(session_id, question)
    out = run_agent(
        agent_question,
        session_id=session_id,
        metadata={"transport": "cli", "route": "main.py"},
        tags=["cli", "sync"],
    )
    append_turn(session_id, "user", question)
    append_turn(session_id, "assistant", out.get("answer") or "")
    return out


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        session = ensure_session(None)
        print(f"\nQuestion: {question}\n")
        _print_run(_run_with_session(question, session["session_id"]))
    else:
        session = ensure_session(None)
        print("Agent GraphRAG - Assurance Maladie")
        print("Tapez 'quit' pour quitter.\n")
        print(f"session_id: {session['session_id']}\n")
        while True:
            question = input("Question: ").strip()
            if question.lower() in ("quit", "exit", "q"):
                break
            if not question:
                continue
            _print_run(_run_with_session(question, session["session_id"]))


def _print_run(out: dict) -> None:
    """Print natural-language answer, Cypher, and trace separately."""
    print("Reponse (natural language):\n")
    print(out.get("answer") or "")
    print("\n--- Cypher genere (separe de la reponse) ---\n")
    cy = (out.get("cypher") or "").strip()
    print(cy if cy else "(aucun)")
    results = list(out.get("results") or [])
    metrics = dict(out.get("metrics") or {})
    llm_calls = list(metrics.get("llm_calls") or [])
    if results:
        print("\n--- Resultats Neo4j sanitises (aperçu) ---\n")
        print(json.dumps(results[:3], indent=2, ensure_ascii=False))
        if len(results) > 3:
            print(f"... {len(results) - 3} ligne(s) supplementaire(s)")
    else:
        print("\n--- Resultats Neo4j sanitises (aperçu) ---\n")
        print("(aucun resultat)")

    print("\n--- Journal pipeline ---\n")
    for idx, trace_step in enumerate(out.get("trace") or [], start=1):
        node = trace_step.get("node") or "unknown"
        event = trace_step.get("event") or "unknown"
        print(f"{idx}. {node}: {event}")
        interesting_fields = [
            "generation_mode",
            "provider",
            "model",
            "schema_mode",
            "schema_chars",
            "focus_labels",
            "reason",
            "error",
            "checks",
            "neo4j_executed",
            "neo4j_explain_ok",
            "row_count",
            "sample_keys",
        ]
        for field in interesting_fields:
            if trace_step.get(field) is not None:
                print(f"   {field}: {trace_step.get(field)}")
        if trace_step.get("sample_rows") is not None:
            print("   sample_rows:")
            print(json.dumps(trace_step.get("sample_rows"), indent=2, ensure_ascii=False))
        if trace_step.get("schema_preview") is not None:
            print("   schema_preview:")
            print(str(trace_step.get("schema_preview")))

    if metrics:
        print("\n--- Metriques run ---\n")
        print(f"latency_ms: {metrics.get('latency_ms')}")
        print(f"ttft_ms: {metrics.get('ttft_ms')}")
        print(f"retry_count: {metrics.get('retry_count')}")
        print(f"llm_call_count: {metrics.get('llm_call_count')}")
        usage = metrics.get("llm_usage") or {}
        print(
            "llm_usage: "
            f"prompt={usage.get('prompt_tokens', 0)}, "
            f"completion={usage.get('completion_tokens', 0)}, "
            f"total={usage.get('total_tokens', 0)}"
        )
        for idx, call in enumerate(llm_calls, start=1):
            usage_details = call.get("usage_details") or {}
            print(
                f"   call_{idx}: provider={call.get('provider')} "
                f"model={call.get('model')} purpose={call.get('purpose')} "
                f"tokens={usage_details.get('total_tokens', 0)}"
            )
    print("\n--- Trace (execution) ---\n")
    print(f"trace_id: {out.get('trace_id') or ''}")
    print(json.dumps(out.get("trace") or [], indent=2, ensure_ascii=False))
    print()


if __name__ == "__main__":
    try:
        main()
    finally:
        shutdown_langfuse()
