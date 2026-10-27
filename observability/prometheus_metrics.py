"""Lightweight in-process Prometheus-style metrics."""

from __future__ import annotations

import math
import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(lambda: defaultdict(float))
_hist_sums: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(lambda: defaultdict(float))
_hist_counts: dict[str, dict[tuple[tuple[str, str], ...], int]] = defaultdict(lambda: defaultdict(int))


def _label_key(**labels: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


def _render_labels(label_key: tuple[tuple[str, str], ...]) -> str:
    if not label_key:
        return ""
    parts = [f'{key}="{value}"' for key, value in label_key]
    return "{" + ",".join(parts) + "}"


def _inc(name: str, value: float = 1.0, **labels: str) -> None:
    with _lock:
        _counters[name][_label_key(**labels)] += float(value)


def _observe(name: str, value: float, **labels: str) -> None:
    with _lock:
        key = _label_key(**labels)
        _hist_sums[name][key] += float(value)
        _hist_counts[name][key] += 1


def inc_chat_requests(route: str, mode: str) -> None:
    _inc("graphrag_chat_requests_total", route=route, mode=mode)


def inc_cypher_retries(reason: str = "validation") -> None:
    _inc("graphrag_cypher_retries_total", reason=reason)


def inc_validation_failures(reason: str) -> None:
    _inc("graphrag_validation_failures_total", reason=reason)


def observe_query_latency(duration_ms: float, mode: str) -> None:
    _observe("graphrag_query_latency_ms", duration_ms, mode=mode)


def observe_node_latency(node: str, duration_ms: float) -> None:
    _observe("graphrag_node_latency_ms", duration_ms, node=node)


def add_llm_tokens_used(count: int, kind: str) -> None:
    if count > 0:
        _inc("graphrag_llm_tokens_used_total", float(count), kind=kind)


def inc_result_sanitizations(field_type: str) -> None:
    _inc("graphrag_result_sanitizations_total", field_type=field_type)


def inc_session_loads(store: str) -> None:
    _inc("graphrag_session_loads_total", store=store)


def inc_session_stores(store: str) -> None:
    _inc("graphrag_session_stores_total", store=store)


def inc_trace_events(event_type: str) -> None:
    _inc("graphrag_trace_events_total", event_type=event_type)


def reset_metrics() -> None:
    with _lock:
        _counters.clear()
        _hist_sums.clear()
        _hist_counts.clear()


def render_metrics() -> str:
    lines: list[str] = [
        "# HELP graphrag_chat_requests_total Total chat requests processed.",
        "# TYPE graphrag_chat_requests_total counter",
        "# HELP graphrag_cypher_retries_total Total validator-triggered Cypher retries.",
        "# TYPE graphrag_cypher_retries_total counter",
        "# HELP graphrag_validation_failures_total Total validation failures by reason.",
        "# TYPE graphrag_validation_failures_total counter",
        "# HELP graphrag_llm_tokens_used_total Estimated LLM token usage.",
        "# TYPE graphrag_llm_tokens_used_total counter",
        "# HELP graphrag_result_sanitizations_total Sensitive result fields sanitized before synthesis.",
        "# TYPE graphrag_result_sanitizations_total counter",
        "# HELP graphrag_session_loads_total Session loads by backing store.",
        "# TYPE graphrag_session_loads_total counter",
        "# HELP graphrag_session_stores_total Session writes by backing store.",
        "# TYPE graphrag_session_stores_total counter",
        "# HELP graphrag_trace_events_total Trace events emitted to observability.",
        "# TYPE graphrag_trace_events_total counter",
        "# HELP graphrag_query_latency_ms_sum Sum of query latency in milliseconds.",
        "# TYPE graphrag_query_latency_ms summary",
        "# HELP graphrag_node_latency_ms_sum Sum of node latency in milliseconds.",
        "# TYPE graphrag_node_latency_ms summary",
    ]
    with _lock:
        for name in sorted(_counters):
            for labels, value in sorted(_counters[name].items()):
                lines.append(f"{name}{_render_labels(labels)} {value}")
        for name in sorted(_hist_sums):
            for labels, value in sorted(_hist_sums[name].items()):
                count = _hist_counts[name].get(labels, 0)
                clean_sum = 0.0 if math.isnan(value) else value
                lines.append(f"{name}_sum{_render_labels(labels)} {clean_sum}")
                lines.append(f"{name}_count{_render_labels(labels)} {count}")
    return "\n".join(lines) + "\n"
