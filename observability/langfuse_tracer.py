"""Official Langfuse v4 tracing helpers with JSONL fallback."""

from __future__ import annotations

import builtins
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from config.settings import get_settings
from observability.prometheus_metrics import inc_trace_events

try:
    from langfuse import get_client, propagate_attributes
except Exception:  # pragma: no cover
    get_client = None
    propagate_attributes = None


class _FallbackObservation:
    def __init__(
        self,
        *,
        name: str,
        as_type: str,
        input_payload: Any = None,
        metadata: dict[str, Any] | None = None,
        model: str | None = None,
        model_parameters: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.as_type = as_type
        self.input = input_payload
        self.metadata = dict(metadata or {})
        self.output: Any = None
        self.model = model
        self.model_parameters = dict(model_parameters or {})
        self.usage_details: dict[str, int] | None = None
        self.status_message: str | None = None
        self._started_at = _utc_now_iso()

    def update(
        self,
        *,
        input: Any = None,
        output: Any = None,
        metadata: Any = None,
        model: str | None = None,
        model_parameters: dict[str, Any] | None = None,
        usage_details: dict[str, int] | None = None,
        status_message: str | None = None,
        **_: Any,
    ) -> None:
        if input is not None:
            self.input = input
        if output is not None:
            self.output = output
        if metadata is not None:
            self.metadata = dict(metadata)
        if model is not None:
            self.model = model
        if model_parameters is not None:
            self.model_parameters = dict(model_parameters)
        if usage_details is not None:
            self.usage_details = dict(usage_details)
        if status_message is not None:
            self.status_message = status_message

    def export(self) -> dict[str, Any]:
        return {
            "started_at": self._started_at,
            "name": self.name,
            "as_type": self.as_type,
            "input": self.input,
            "output": self.output,
            "metadata": self.metadata,
            "model": self.model,
            "model_parameters": self.model_parameters,
            "usage_details": self.usage_details,
            "status_message": self.status_message,
        }


_client: Any = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path_str: str) -> None:
    path = Path(path_str)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def _append_jsonl(record: dict[str, Any]) -> None:
    path = get_settings().OBSERVABILITY_LOG_PATH
    _ensure_parent_dir(path)
    try:
        with builtins.open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        return


def _safe_context_exit(
    cm: Any,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    tb: Any,
) -> bool:
    if cm is None:
        return False
    try:
        return bool(cm.__exit__(exc_type, exc, tb))
    except Exception:
        return False


def _coerce_string_map(payload: dict[str, Any] | None) -> dict[str, str] | None:
    if not payload:
        return None
    out: dict[str, str] = {}
    for key, value in payload.items():
        if value is None:
            continue
        out[str(key)] = str(value)
    return out or None


def _apply_langfuse_environment() -> None:
    s = get_settings()
    if s.LANGFUSE_PUBLIC_KEY:
        os.environ["LANGFUSE_PUBLIC_KEY"] = s.LANGFUSE_PUBLIC_KEY
    if s.LANGFUSE_SECRET_KEY:
        os.environ["LANGFUSE_SECRET_KEY"] = s.LANGFUSE_SECRET_KEY
    base_url = s.langfuse_base_url()
    if base_url:
        os.environ["LANGFUSE_BASE_URL"] = base_url


def _is_enabled() -> bool:
    s = get_settings()
    if getattr(s, "DEMO_MODE", False):
        return False
    return bool(
        s.LANGFUSE_TRACING_ENABLED
        and s.LANGFUSE_PUBLIC_KEY
        and s.LANGFUSE_SECRET_KEY
        and get_client is not None
    )


def _get_langfuse_client() -> Any:
    global _client
    if _client is not None:
        return _client
    if not _is_enabled():
        return None
    try:
        _apply_langfuse_environment()
        _client = get_client()
        return _client
    except Exception:
        _client = None
        return None


def auth_check_langfuse() -> bool:
    client = _get_langfuse_client()
    if client is None:
        return False
    try:
        return bool(client.auth_check())
    except Exception:
        return False


def get_current_trace_id() -> str | None:
    client = _get_langfuse_client()
    if client is None:
        return None
    try:
        return client.get_current_trace_id()
    except Exception:
        return None


@contextmanager
def trace_attributes(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    trace_name: str | None = None,
) -> Iterator[None]:
    if not _is_enabled() or propagate_attributes is None:
        yield
        return

    try:
        propagation_cm = propagate_attributes(
            user_id=user_id,
            session_id=session_id,
            metadata=_coerce_string_map(metadata),
            tags=tags,
            trace_name=trace_name,
        )
        propagation_cm.__enter__()
    except Exception:
        yield
        return

    try:
        yield
    except Exception as exc:
        if not _safe_context_exit(propagation_cm, type(exc), exc, exc.__traceback__):
            raise
    else:
        _safe_context_exit(propagation_cm, None, None, None)


@contextmanager
def start_observation(
    *,
    name: str,
    as_type: str,
    input_payload: Any = None,
    metadata: dict[str, Any] | None = None,
    trace_context: dict[str, str] | None = None,
    model: str | None = None,
    model_parameters: dict[str, Any] | None = None,
) -> Iterator[Any]:
    record_base = {
        "ts": _utc_now_iso(),
        "type": "observation",
        "name": name,
        "as_type": as_type,
    }
    client = _get_langfuse_client()
    if client is None:
        observation = _FallbackObservation(
            name=name,
            as_type=as_type,
            input_payload=input_payload,
            metadata=metadata,
            model=model,
            model_parameters=model_parameters,
        )
        try:
            yield observation
        finally:
            inc_trace_events("observation")
            _append_jsonl({**record_base, **observation.export()})
        return

    try:
        observation_cm = client.start_as_current_observation(
            trace_context=trace_context,
            name=name,
            as_type=as_type,
            input=input_payload,
            metadata=metadata,
            model=model,
            model_parameters=model_parameters,
        )
        observation = observation_cm.__enter__()
    except Exception:
        observation = _FallbackObservation(
            name=name,
            as_type=as_type,
            input_payload=input_payload,
            metadata=metadata,
            model=model,
            model_parameters=model_parameters,
        )
        try:
            yield observation
        finally:
            inc_trace_events("observation")
            _append_jsonl({**record_base, **observation.export()})
        return

    inc_trace_events("observation")
    try:
        yield observation
    except Exception as exc:
        try:
            observation.update(status_message=str(exc))
        except Exception:
            pass
        if not _safe_context_exit(
            observation_cm,
            type(exc),
            exc,
            exc.__traceback__,
        ):
            raise
    else:
        _safe_context_exit(observation_cm, None, None, None)


def trace_event(name: str, metadata: dict[str, Any]) -> None:
    record = {
        "ts": _utc_now_iso(),
        "type": "event",
        "name": name,
        "metadata": metadata,
    }
    client = _get_langfuse_client()
    if client is not None:
        try:
            client.create_event(name=name, metadata=metadata)
            inc_trace_events("event")
            return
        except Exception:
            pass
    inc_trace_events("event")
    _append_jsonl(record)


def flush_langfuse() -> None:
    client = _get_langfuse_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        return


def shutdown_langfuse() -> None:
    client = _get_langfuse_client()
    if client is None:
        return
    try:
        client.shutdown()
    except Exception:
        try:
            client.flush()
        except Exception:
            return
