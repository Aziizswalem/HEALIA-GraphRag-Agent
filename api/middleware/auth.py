"""JWT validation + basic RBAC middleware."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config.settings import get_settings

_EXEMPT_PATHS = ("/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json")
_HMAC_ALGORITHMS = {
    "HS256": hashlib.sha256,
    "HS384": hashlib.sha384,
    "HS512": hashlib.sha512,
}


def _anonymous_auth_context() -> dict[str, Any]:
    return {
        "authenticated": False,
        "user_id": None,
        "roles": [],
        "source": "anonymous",
        "claims": {},
    }


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _extract_roles(claims: dict[str, Any]) -> list[str]:
    roles = claims.get("roles")
    if isinstance(roles, str):
        return [r.strip() for r in roles.split(",") if r.strip()]
    if isinstance(roles, list):
        return [str(r).strip() for r in roles if str(r).strip()]
    role = claims.get("role")
    if isinstance(role, str) and role.strip():
        return [role.strip()]
    return []


def verify_jwt(token: str) -> dict[str, Any] | None:
    s = get_settings()
    secret = (s.JWT_SECRET or "").strip()
    algorithm = (s.JWT_ALGORITHM or "HS256").strip().upper()
    digestmod = _HMAC_ALGORITHMS.get(algorithm)
    if not token or not secret or digestmod is None:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, signature_b64 = parts
    try:
        header = json.loads(_base64url_decode(header_b64))
        payload = json.loads(_base64url_decode(payload_b64))
        signature = _base64url_decode(signature_b64)
    except Exception:
        return None

    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None
    if str(header.get("alg", "")).upper() != algorithm:
        return None

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, digestmod).digest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    now = int(time.time())
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    if isinstance(exp, (int, float)) and now >= int(exp):
        return None
    if isinstance(nbf, (int, float)) and now < int(nbf):
        return None

    return payload


def get_request_auth_context(request: Request) -> dict[str, Any]:
    return getattr(request.state, "auth_context", _anonymous_auth_context())


class AuthMiddleware(BaseHTTPMiddleware):
    """Protect application routes with Bearer JWT when configured."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        s = get_settings()
        auth_context = _anonymous_auth_context()
        request.state.auth_context = auth_context

        if path in _EXEMPT_PATHS:
            return await call_next(request)

        secret = (s.JWT_SECRET or "").strip()

        # Trust the Odoo-proxied user header (comes from authenticated Odoo session)
        odoo_user = request.headers.get("X-Odoo-User", "").strip()
        if odoo_user:
            auth_context = {
                "authenticated": True,
                "user_id": odoo_user,
                "roles": ["admin"],
                "source": "odoo",
                "claims": {},
            }
            request.state.auth_context = auth_context
            return await call_next(request)

        if not secret:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Bearer token."},
            )

        token = authorization.split(" ", 1)[1].strip()
        claims = verify_jwt(token)
        if claims is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token."},
            )

        roles = _extract_roles(claims)
        auth_context = {
            "authenticated": True,
            "user_id": str(claims.get("sub") or claims.get("user_id") or "unknown"),
            "roles": roles,
            "source": "jwt",
            "claims": claims,
        }
        request.state.auth_context = auth_context

        return await call_next(request)
