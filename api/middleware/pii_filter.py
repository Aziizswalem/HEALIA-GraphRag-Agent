"""Request-level PII redaction before LLM calls."""

from __future__ import annotations

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import Message

from config.settings import get_settings
from guardrails.pii_detector import detect_and_redact_pii, redact_pii

_CHAT_PATHS = {"/chat"}


def filter_body(text: str) -> str:
    return redact_pii(text)


def _install_body_override(request: Request, body: bytes) -> None:
    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    request._body = body
    request._receive = receive


class PIIFilterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        s = get_settings()
        if (
            not s.PII_FILTER_ENABLED
            or request.method.upper() != "POST"
            or request.url.path not in _CHAT_PATHS
        ):
            return await call_next(request)

        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return await call_next(request)

        raw_body = await request.body()
        if not raw_body:
            return await call_next(request)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            _install_body_override(request, raw_body)
            return await call_next(request)

        if not isinstance(payload, dict) or not isinstance(payload.get("message"), str):
            _install_body_override(request, raw_body)
            return await call_next(request)

        original_message = payload["message"]
        filtered_message, redactions = detect_and_redact_pii(original_message)
        payload["message"] = filtered_message
        new_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        _install_body_override(request, new_body)

        request.state.original_message = original_message
        request.state.redacted_message = filtered_message
        request.state.pii_redactions = redactions
        request.state.audit_body_preview = {"message": filtered_message}

        response = await call_next(request)
        if redactions:
            response.headers["X-PII-Redactions"] = str(len(redactions))
        return response
