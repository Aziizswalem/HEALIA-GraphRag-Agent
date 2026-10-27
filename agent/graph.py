from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from typing import Any, TypedDict, cast

from langgraph.graph import END, StateGraph

from agent.edges import after_execution, after_validation
from agent.state import AgentState
from agent.nodes import (
    cypher_generator,
    cypher_validator,
    fallback,
    graph_executor,
    schema_retriever,
    synthesizer,
    genui_renderer,
    intent_classifier,
    shortcut_resolver,
)
from observability.langfuse_tracer import (
    get_current_trace_id,
    start_observation,
    trace_attributes,
)
from observability.prometheus_metrics import (
    add_llm_tokens_used,
    inc_cypher_retries,
    inc_validation_failures,
    observe_node_latency,
    observe_query_latency,
)
from observability.run_metrics import capture_run_metrics, snapshot_run_metrics


class AgentRunResult(TypedDict, total=False):
    """Structured output: natural-language answer is separate from generated Cypher."""

    answer: str
    cypher: str
    results: list[dict[str, Any]]
    trace_id: str
    trace: list[dict[str, Any]]
    metrics: dict[str, Any]
    genui_blocks: list[dict[str, Any]]


class AgentStreamEvent(TypedDict, total=False):
    type: str
    trace_id: str
    cypher: str
    token: str
    answer: str
    trace: list[dict[str, Any]]
    step: dict[str, Any]
    node: str
    results: list[dict[str, Any]]
    retry_count: int
    validation_error: str
    question: str
    pii_redactions: list[dict[str, str]]
    warning: str
    session_id: str
    genui_blocks: list[dict[str, Any]]


_NODE_MODULES = {
    "intent_classifier": intent_classifier,
    "schema_retriever": schema_retriever,
    "cypher_generator": cypher_generator,
    "cypher_validator": cypher_validator,
    "graph_executor": graph_executor,
    "synthesizer": synthesizer,
    "genui_renderer": genui_renderer,
    "fallback": fallback,
    "shortcut_resolver": shortcut_resolver,
}

_NODE_TYPES = {
    "schema_retriever": "retriever",
    "cypher_generator": "chain",
    "cypher_validator": "guardrail",
    "graph_executor": "tool",
    "synthesizer": "generation",
    "genui_renderer": "generation",
    "fallback": "guardrail",
}


def _estimate_tokens(text: str) -> int:
    return len([part for part in (text or "").split() if part])


def _after_intent(state: AgentState) -> str:
    """Route after the intent classifier: query the DB, run a shortcut, or finish."""
    steps = state.get("trace_steps") or []
    for st in steps:
        if st.get("event") == "route_shortcut":
            return "shortcut"
    if state.get("final_answer"):
        return "done"
    return "schema_retriever"


def _node_input(node_name: str, state: AgentState) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "retry_count": int(state.get("retry_count") or 0),
    }
    if node_name == "schema_retriever":
        payload["question"] = state.get("question") or ""
    elif node_name == "cypher_generator":
        payload["question"] = state.get("question") or ""
        payload["validation_error"] = state.get("validation_error")
    elif node_name == "cypher_validator":
        payload["cypher_draft"] = state.get("cypher_draft") or ""
    elif node_name == "graph_executor":
        payload["cypher_draft"] = state.get("cypher_draft") or ""
    elif node_name == "synthesizer":
        payload["result_count"] = len(state.get("graph_results") or [])
    return payload


def _node_output_summary(updates: dict[str, Any]) -> dict[str, Any]:
    trace_steps = list(updates.get("trace_steps") or [])
    summary: dict[str, Any] = {}
    if trace_steps:
        summary["event"] = trace_steps[0].get("event")
        if trace_steps[0].get("reason") is not None:
            summary["reason"] = trace_steps[0].get("reason")
    if "validation_error" in updates:
        summary["validation_error"] = updates.get("validation_error")
    if "cypher_draft" in updates:
        summary["cypher_draft"] = updates.get("cypher_draft")
    if "final_answer" in updates:
        summary["final_answer"] = updates.get("final_answer")
    if "graph_results" in updates and isinstance(updates.get("graph_results"), list):
        summary["graph_result_count"] = len(updates["graph_results"])
    return summary


def _invoke_node(node_name: str, state: AgentState) -> dict[str, Any]:
    session_id = state.get("session_id")
    if session_id:
        from memory.session_manager import get_session
        session = get_session(session_id)
        if session and session.get("cancelled"):
            raise Exception("Agent execution cancelled by user")

    module = _NODE_MODULES[node_name]
    started = time.perf_counter()
    with start_observation(
        name=node_name,
        as_type=_NODE_TYPES.get(node_name, "span"),
        input_payload=_node_input(node_name, state),
        metadata={"trace_id": state.get("trace_id") or ""},
    ) as observation:
        updates = module.run(state)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        output_summary = _node_output_summary(updates)
        observation.update(
            output=output_summary,
            metadata={
                "duration_ms": duration_ms,
                "retry_count": updates.get("retry_count", state.get("retry_count", 0)),
            },
        )

    observe_node_latency(duration_ms=duration_ms, node=node_name)
    steps = list(updates.get("trace_steps") or [])
    first_step = steps[0] if steps else {}
    reason = str(first_step.get("reason") or "")
    event = str(first_step.get("event") or "")
    if node_name == "cypher_validator" and event == "invalid":
        inc_validation_failures(reason or "unknown")
        if state.get("retry_count", 0) < updates.get("retry_count", 0):
            inc_cypher_retries(reason or "validation")
    return updates


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    for node_name in _NODE_MODULES:
        graph.add_node(node_name, lambda state, _name=node_name: _invoke_node(_name, state))

    graph.set_entry_point("intent_classifier")
    graph.add_conditional_edges(
        "intent_classifier",
        _after_intent,
        {
            "schema_retriever": "schema_retriever",
            "shortcut": "shortcut_resolver",
            "done": END,
        },
    )
    graph.add_edge("shortcut_resolver", END)
    graph.add_edge("schema_retriever", "cypher_generator")
    graph.add_edge("cypher_generator", "cypher_validator")

    graph.add_conditional_edges(
        "cypher_validator",
        after_validation,
        {
            "execute": "graph_executor",
            "retry": "cypher_generator",
            "fallback": "fallback",
        },
    )

    graph.add_conditional_edges(
        "graph_executor",
        after_execution,
        {
            "synthesize": "synthesizer",
            "done": END,
        },
    )

    graph.add_edge("synthesizer", "genui_renderer")
    graph.add_edge("genui_renderer", END)
    graph.add_edge("fallback", END)
    return graph.compile()


agent = build_graph()


def _initial_state(question: str, session_id: str | None = None) -> AgentState:
    return {
        "question": question,
        "schema_context": "",
        "cypher_draft": "",
        "validation_error": None,
        "graph_results": None,
        "retry_count": 0,
        "final_answer": "",
        "trace_id": uuid.uuid4().hex,
        "trace_steps": [],
        "session_id": session_id,
        "genui_blocks": None,
    }


def _apply_updates(state: AgentState, updates: dict[str, Any]) -> AgentState:
    merged = dict(state)
    extra_steps = list(updates.get("trace_steps") or [])
    for key, value in updates.items():
        if key == "trace_steps":
            continue
        merged[key] = value
    if extra_steps:
        merged["trace_steps"] = [*list(state.get("trace_steps") or []), *extra_steps]
    return cast(AgentState, merged)


def _run_node(state: AgentState, node_name: str) -> tuple[AgentState, list[dict[str, Any]]]:
    updates = _invoke_node(node_name, state)
    next_state = _apply_updates(state, updates)
    return next_state, list(updates.get("trace_steps") or [])


def _emit_run_metrics(
    *,
    state: AgentState,
    duration_ms: float,
    mode: str,
) -> None:
    answer = state.get("final_answer") or ""
    cypher = (state.get("cypher_draft") or "").strip()
    add_llm_tokens_used(_estimate_tokens(answer), kind="answer")
    add_llm_tokens_used(_estimate_tokens(cypher), kind="cypher")
    observe_query_latency(duration_ms=duration_ms, mode=mode)


def run_agent(
    question: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> AgentRunResult:
    """
    Run the full LangGraph loop and return answer, final Cypher draft, and trace steps.
    Cypher is returned separately; it must not be repeated inside `answer`.
    """
    initial_state = _initial_state(question, session_id)
    started = time.perf_counter()

    with start_observation(
        name="graphrag-agent-run",
        as_type="agent",
        trace_context={"trace_id": initial_state["trace_id"]},
        input_payload={"question": question, "mode": "sync"},
        metadata=metadata or {},
    ) as root_observation:
        with capture_run_metrics() as run_metrics:
            with trace_attributes(
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
                tags=tags,
                trace_name="graphrag-agent-run",
            ):
                result = agent.invoke(initial_state)
                final_state = cast(AgentState, result)
                final_state["trace_id"] = get_current_trace_id() or initial_state["trace_id"]
                duration_ms = (time.perf_counter() - started) * 1000
                _emit_run_metrics(state=final_state, duration_ms=duration_ms, mode="sync")
                root_observation.update(
                    output={
                        "answer": final_state.get("final_answer") or "",
                        "cypher": (final_state.get("cypher_draft") or "").strip(),
                        "retry_count": int(final_state.get("retry_count") or 0),
                    },
                    metadata={
                        "duration_ms": round(duration_ms, 3),
                        "trace_id": final_state["trace_id"],
                        "mode": "sync",
                    },
                )
        run_snapshot = snapshot_run_metrics(run_metrics)

    return {
        "answer": final_state.get("final_answer") or "",
        "cypher": (final_state.get("cypher_draft") or "").strip(),
        "results": list(final_state.get("graph_results") or []),
        "trace_id": final_state.get("trace_id") or "",
        "trace": list(final_state.get("trace_steps") or []),
        "genui_blocks": list(final_state.get("genui_blocks") or []),
        "metrics": {
            "latency_ms": round(duration_ms, 3),
            "retry_count": int(final_state.get("retry_count") or 0),
            **run_snapshot,
        },
    }


def run_agent_stream(
    question: str,
    *,
    pii_redactions: list[dict[str, str]] | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[AgentStreamEvent]:
    state = _initial_state(question, session_id)
    started = time.perf_counter()
    warning: str | None = None

    with start_observation(
        name="graphrag-agent-run",
        as_type="agent",
        trace_context={"trace_id": state["trace_id"]},
        input_payload={"question": question, "mode": "stream"},
        metadata=metadata or {},
    ) as root_observation:
        with trace_attributes(
            user_id=user_id,
            session_id=session_id,
            metadata=metadata,
            tags=tags,
            trace_name="graphrag-agent-run",
        ):
            current_trace_id = get_current_trace_id() or state["trace_id"]
            state["trace_id"] = current_trace_id
            yield {
                "type": "start",
                "trace_id": current_trace_id,
                "question": question,
                "pii_redactions": list(pii_redactions or []),
                "session_id": session_id or "",
            }

            yield {"type": "node_start", "trace_id": state["trace_id"], "node": "intent_classifier"}
            state, steps = _run_node(state, "intent_classifier")
            for trace_step in steps:
                yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
            yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "intent_classifier"}

            if _after_intent(state) == "done":
                final_answer = state.get("final_answer") or ""
                if final_answer:
                    yield {"type": "token", "trace_id": state["trace_id"], "token": final_answer}
                duration_ms = (time.perf_counter() - started) * 1000
                _emit_run_metrics(state=state, duration_ms=duration_ms, mode="stream")
                root_observation.update(
                    output={
                        "answer": final_answer,
                        "cypher": "",
                        "retry_count": int(state.get("retry_count") or 0),
                    },
                    metadata={
                        "duration_ms": round(duration_ms, 3),
                        "trace_id": state["trace_id"],
                        "mode": "stream",
                    },
                )
                yield {
                    "type": "final",
                    "trace_id": state["trace_id"],
                    "answer": final_answer,
                    "cypher": "",
                    "results": [],
                    "trace": list(state.get("trace_steps") or []),
                    "session_id": session_id or "",
                    "genui_blocks": [],
                }
                return

            if _after_intent(state) == "shortcut":
                yield {"type": "node_start", "trace_id": state["trace_id"], "node": "shortcut_resolver"}
                state, steps = _run_node(state, "shortcut_resolver")
                for trace_step in steps:
                    yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
                yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "shortcut_resolver"}
                final_answer = state.get("final_answer") or ""
                if final_answer:
                    yield {"type": "token", "trace_id": state["trace_id"], "token": final_answer}
                duration_ms = (time.perf_counter() - started) * 1000
                _emit_run_metrics(state=state, duration_ms=duration_ms, mode="stream")
                root_observation.update(
                    output={
                        "answer": final_answer,
                        "cypher": (state.get("cypher_draft") or "").strip(),
                        "retry_count": int(state.get("retry_count") or 0),
                    },
                    metadata={
                        "duration_ms": round(duration_ms, 3),
                        "trace_id": state["trace_id"],
                        "mode": "stream",
                    },
                )
                yield {
                    "type": "final",
                    "trace_id": state["trace_id"],
                    "answer": final_answer,
                    "cypher": (state.get("cypher_draft") or "").strip(),
                    "results": list(state.get("graph_results") or []),
                    "trace": list(state.get("trace_steps") or []),
                    "session_id": session_id or "",
                    "genui_blocks": list(state.get("genui_blocks") or []),
                }
                return

            yield {"type": "node_start", "trace_id": state["trace_id"], "node": "schema_retriever"}
            state, steps = _run_node(state, "schema_retriever")
            for trace_step in steps:
                yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
            yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "schema_retriever"}

            yield {"type": "node_start", "trace_id": state["trace_id"], "node": "cypher_generator"}
            state, steps = _run_node(state, "cypher_generator")
            for trace_step in steps:
                yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
            yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "cypher_generator"}

            while True:
                yield {"type": "node_start", "trace_id": state["trace_id"], "node": "cypher_validator"}
                state, steps = _run_node(state, "cypher_validator")
                for trace_step in steps:
                    yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
                yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "cypher_validator"}

                next_step = after_validation(state)
                if next_step == "retry":
                    yield {
                        "type": "retry",
                        "trace_id": state["trace_id"],
                        "retry_count": int(state.get("retry_count") or 0),
                        "validation_error": str(state.get("validation_error") or ""),
                    }
                    yield {"type": "node_start", "trace_id": state["trace_id"], "node": "cypher_generator"}
                    state, steps = _run_node(state, "cypher_generator")
                    for trace_step in steps:
                        yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
                    yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "cypher_generator"}
                    continue

                if next_step == "fallback":
                    yield {"type": "node_start", "trace_id": state["trace_id"], "node": "fallback"}
                    state, steps = _run_node(state, "fallback")
                    for trace_step in steps:
                        yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
                    yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "fallback"}
                    final_answer = state.get("final_answer") or ""
                    if final_answer:
                        yield {"type": "token", "trace_id": state["trace_id"], "token": final_answer}
                    duration_ms = (time.perf_counter() - started) * 1000
                    _emit_run_metrics(state=state, duration_ms=duration_ms, mode="stream")
                    root_observation.update(
                        output={
                            "answer": final_answer,
                            "cypher": (state.get("cypher_draft") or "").strip(),
                            "retry_count": int(state.get("retry_count") or 0),
                        },
                        metadata={
                            "duration_ms": round(duration_ms, 3),
                            "trace_id": state["trace_id"],
                            "mode": "stream",
                        },
                    )
                    yield {
                        "type": "final",
                        "trace_id": state["trace_id"],
                        "answer": final_answer,
                        "cypher": (state.get("cypher_draft") or "").strip(),
                        "results": list(state.get("graph_results") or []),
                        "trace": list(state.get("trace_steps") or []),
                        "session_id": session_id or "",
                        "genui_blocks": [],
                    }
                    return

                break

            yield {"type": "node_start", "trace_id": state["trace_id"], "node": "graph_executor"}
            state, steps = _run_node(state, "graph_executor")
            for trace_step in steps:
                yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
            yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "graph_executor"}

            if after_execution(state) == "done":
                final_answer = state.get("final_answer") or ""
                if final_answer:
                    yield {"type": "token", "trace_id": state["trace_id"], "token": final_answer}
                duration_ms = (time.perf_counter() - started) * 1000
                _emit_run_metrics(state=state, duration_ms=duration_ms, mode="stream")
                root_observation.update(
                    output={
                        "answer": final_answer,
                        "cypher": (state.get("cypher_draft") or "").strip(),
                        "retry_count": int(state.get("retry_count") or 0),
                    },
                    metadata={
                        "duration_ms": round(duration_ms, 3),
                        "trace_id": state["trace_id"],
                        "mode": "stream",
                    },
                )
                yield {
                    "type": "final",
                    "trace_id": state["trace_id"],
                    "answer": final_answer,
                    "cypher": (state.get("cypher_draft") or "").strip(),
                    "results": list(state.get("graph_results") or []),
                    "trace": list(state.get("trace_steps") or []),
                    "session_id": session_id or "",
                    "genui_blocks": [],
                }
                return

            yield {
                "type": "cypher",
                "trace_id": state["trace_id"],
                "cypher": (state.get("cypher_draft") or "").strip(),
            }

            chunks: list[str] = []
            stream_failed = False
            total_rows = 0
            try:
                stream_started = time.perf_counter()
                yield {"type": "node_start", "trace_id": state["trace_id"], "node": "synthesizer"}
                token_iter, total_rows = synthesizer.stream(state)
                for token in token_iter:
                    if not token:
                        continue
                    chunks.append(token)
                    yield {"type": "token", "trace_id": state["trace_id"], "token": token}
                observe_node_latency(
                    node="synthesizer_stream",
                    duration_ms=(time.perf_counter() - stream_started) * 1000,
                )
            except Exception:
                stream_failed = True
                total_rows = len(state.get("graph_results") or [])

            if stream_failed and not chunks:
                updates = _invoke_node("synthesizer", state)
                state = _apply_updates(state, updates)
                final_answer = state.get("final_answer") or ""
                if final_answer:
                    yield {"type": "token", "trace_id": state["trace_id"], "token": final_answer}
                for trace_step in updates.get("trace_steps") or []:
                    yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
                warning = "Streaming fallback applied using non-stream synthesis."
                yield {
                    "type": "warning",
                    "trace_id": state["trace_id"],
                    "warning": warning,
                }
            else:
                final_answer = "".join(chunks).strip()
                updates = synthesizer.finalize_streamed_answer(
                    final_answer=final_answer,
                    total_rows=total_rows,
                )
                state = _apply_updates(state, updates)
                for trace_step in updates.get("trace_steps") or []:
                    yield {"type": "trace", "trace_id": state["trace_id"], "step": trace_step}
            yield {"type": "node_complete", "trace_id": state["trace_id"], "node": "synthesizer"}

            duration_ms = (time.perf_counter() - started) * 1000
            _emit_run_metrics(state=state, duration_ms=duration_ms, mode="stream")
            root_observation.update(
                output={
                    "answer": state.get("final_answer") or "",
                    "cypher": (state.get("cypher_draft") or "").strip(),
                    "retry_count": int(state.get("retry_count") or 0),
                    "warning": warning,
                },
                metadata={
                    "duration_ms": round(duration_ms, 3),
                    "trace_id": state["trace_id"],
                    "mode": "stream",
                },
            )
            yield {
                "type": "final",
                "trace_id": state["trace_id"],
                "answer": state.get("final_answer") or "",
                "cypher": (state.get("cypher_draft") or "").strip(),
                "results": list(state.get("graph_results") or []),
                "trace": list(state.get("trace_steps") or []),
                "session_id": session_id or "",
                "genui_blocks": list(state.get("genui_blocks") or []),
            }


def ask(question: str) -> str:
    """Backward-compatible: return only the natural-language answer."""
    return run_agent(question)["answer"]
