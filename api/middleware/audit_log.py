"""Structured audit logging with resilient file fallback."""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import Message

from config.settings import get_settings

try:
    import psycopg  # type: ignore
except Exception:  # pragma: no cover
    psycopg = None

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None

_SENSITIVE_HEADERS = {"authorization", "cookie", "x-admin-key"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _install_body_override(request: Request, body: bytes) -> None:
    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    request._body = body
    request._receive = receive


def _safe_decode(raw: bytes, limit: int = 2000) -> str:
    text = raw.decode("utf-8", errors="replace")
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in _SENSITIVE_HEADERS:
            out[key] = "<redacted>"
        else:
            out[key] = value
    return out


def _ensure_parent_dir(path_str: str) -> None:
    path = Path(path_str)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def _write_jsonl(path_str: str, record: dict[str, Any]) -> None:
    _ensure_parent_dir(path_str)
    with open(path_str, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_sqlite(path_str: str, record: dict[str, Any]) -> None:
    if path_str.startswith("sqlite:///"):
        db_path = path_str[len("sqlite:///") :]
    else:
        db_path = path_str
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO audit_events (ts, event_type, payload_json) VALUES (?, ?, ?)",
            (record["ts"], record["event_type"], json.dumps(record, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def _write_postgres(database_url: str, record: dict[str, Any]) -> bool:
    payload_json = json.dumps(record, ensure_ascii=False)
    if psycopg is not None:
        conn = psycopg.connect(database_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id SERIAL PRIMARY KEY,
                        ts TIMESTAMPTZ NOT NULL,
                        event_type TEXT NOT NULL,
                        payload_json JSONB NOT NULL
                    )
                    """
                )
                cur.execute(
                    "INSERT INTO audit_events (ts, event_type, payload_json) VALUES (%s, %s, %s::jsonb)",
                    (record["ts"], record["event_type"], payload_json),
                )
            conn.commit()
            return True
        finally:
            conn.close()

    if psycopg2 is not None:
        conn = psycopg2.connect(database_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id SERIAL PRIMARY KEY,
                        ts TIMESTAMPTZ NOT NULL,
                        event_type TEXT NOT NULL,
                        payload_json JSONB NOT NULL
                    )
                    """
                )
                cur.execute(
                    "INSERT INTO audit_events (ts, event_type, payload_json) VALUES (%s, %s, %s::jsonb)",
                    (record["ts"], record["event_type"], payload_json),
                )
            conn.commit()
            return True
        finally:
            conn.close()

    return False


def log_event(event: str, data: dict[str, Any]) -> None:
    s = get_settings()
    if not s.AUDIT_LOG_ENABLED:
        return

    record = {
        "ts": _utc_now_iso(),
        "event_type": event,
        **data,
    }
    database_url = (s.DATABASE_URL or "").strip()
    try:
        if database_url.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
            if _write_postgres(database_url, record):
                return
        elif database_url.startswith("sqlite:///"):
            _write_sqlite(database_url, record)
            return
    except Exception:
        pass

    _write_jsonl(s.AUDIT_LOG_PATH, record)


def log_request(path: str, payload: dict[str, Any]) -> None:
    log_event("request", {"path": path, "payload": payload})


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        s = get_settings()
        if not s.AUDIT_LOG_ENABLED:
            return await call_next(request)

        raw_body = await request.body()
        _install_body_override(request, raw_body)

        started = time.perf_counter()
        request_preview = getattr(request.state, "audit_body_preview", None)
        if request_preview is None and raw_body:
            request_preview = _safe_decode(raw_body)

        try:
            response = await call_next(request)
            status_code = response.status_code
            error_text = None
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            auth_context = getattr(request.state, "auth_context", None) or {}
            request_preview = getattr(request.state, "audit_body_preview", request_preview)
            log_event(
                "http_request",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "request_headers": _sanitize_headers(dict(request.headers)),
                    "request_body": request_preview,
                    "response_headers": {},
                    "response_body_size": None,
                    "user_id": auth_context.get("user_id"),
                    "roles": auth_context.get("roles", []),
                    "pii_redaction_count": len(getattr(request.state, "pii_redactions", []) or []),
                    "rate_limit": getattr(request.state, "rate_limit", None).__dict__
                    if getattr(request.state, "rate_limit", None) is not None
                    else None,
                    "error": str(exc),
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        auth_context = getattr(request.state, "auth_context", None) or {}
        rate_limit = getattr(request.state, "rate_limit", None)
        request_preview = getattr(request.state, "audit_body_preview", request_preview)
        response_body_size = None
        if getattr(response, "body", None) is not None:
            try:
                response_body_size = len(response.body)
            except Exception:
                response_body_size = None

        log_event(
            "http_request",
            {
                "method": request.method,
                "path": request.url.path,
                "query": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "request_headers": _sanitize_headers(dict(request.headers)),
                "request_body": request_preview,
                "response_headers": _sanitize_headers(dict(response.headers)),
                "response_body_size": response_body_size,
                "user_id": auth_context.get("user_id"),
                "roles": auth_context.get("roles", []),
                "pii_redaction_count": len(getattr(request.state, "pii_redactions", []) or []),
                "rate_limit": rate_limit.__dict__ if rate_limit is not None else None,
                "error": error_text,
            },
        )
        return response
