"""Per-run in-memory capture for lightweight evaluation metrics."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from typing import Any, Iterator

_current_run_metrics: ContextVar[dict[str, Any] | None] = ContextVar(
    "current_run_metrics",
    default=None,
)


def _blank_usage() -> dict[str, int]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


@contextmanager
def capture_run_metrics() -> Iterator[dict[str, Any]]:
    """Collect LLM usage emitted during a single agent run."""
    payload: dict[str, Any] = {
        "llm_usage": _blank_usage(),
        "llm_calls": [],
        "ttft_ms": None,
    }
    token = _current_run_metrics.set(payload)
    try:
        yield payload
    finally:
        _current_run_metrics.reset(token)


def record_ttft(ttft_ms: float, *, purpose: str = "") -> None:
    """Record a Time-To-First-Token measurement (milliseconds).

    Only the *first* TTFT recorded per run is kept (the cypher-generation
    call, which is the one users perceive).  Subsequent calls (e.g. the
    synthesizer) are stored in ``ttft_all`` for optional analysis.
    """
    current = _current_run_metrics.get()
    if current is None:
        return

    entry = {"ttft_ms": round(ttft_ms, 3), "purpose": str(purpose or "")}

    # Always append to the full list
    ttft_all: list[dict[str, Any]] = current.setdefault("ttft_all", [])
    ttft_all.append(entry)

    # Keep the first measurement as the headline TTFT
    if current.get("ttft_ms") is None:
        current["ttft_ms"] = round(ttft_ms, 3)


def record_llm_call(
    *,
    provider: str,
    model: str,
    purpose: str,
    usage_details: dict[str, int] | None,
) -> None:
    """Append one LLM call and aggregate token usage when capture is active."""
    current = _current_run_metrics.get()
    if current is None:
        return

    usage = dict(usage_details or {})
    call_record = {
        "provider": str(provider or ""),
        "model": str(model or ""),
        "purpose": str(purpose or ""),
        "usage_details": {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        },
    }

    if call_record["usage_details"]["total_tokens"] <= 0:
        call_record["usage_details"]["total_tokens"] = (
            call_record["usage_details"]["prompt_tokens"]
            + call_record["usage_details"]["completion_tokens"]
        )

    current["llm_calls"].append(call_record)
    aggregate = current["llm_usage"]
    for key, value in call_record["usage_details"].items():
        aggregate[key] = int(aggregate.get(key, 0) or 0) + int(value or 0)


def snapshot_run_metrics(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "llm_usage": _blank_usage(),
            "llm_calls": [],
            "llm_call_count": 0,
            "ttft_ms": None,
            "ttft_all": [],
        }

    snapshot = deepcopy(payload)
    snapshot["llm_call_count"] = len(snapshot.get("llm_calls") or [])
    usage = snapshot.get("llm_usage") or {}
    usage["total_tokens"] = int(usage.get("total_tokens", 0) or 0)
    usage["prompt_tokens"] = int(usage.get("prompt_tokens", 0) or 0)
    usage["completion_tokens"] = int(usage.get("completion_tokens", 0) or 0)
    snapshot["llm_usage"] = usage
    snapshot.setdefault("ttft_ms", None)
    snapshot.setdefault("ttft_all", [])
    return snapshot
