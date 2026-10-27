"""Create / load / list chat sessions (PostgreSQL via SQLAlchemy)."""
from __future__ import annotations

import uuid
from typing import Any

from config.settings import get_settings


def _utc_ts() -> float:
    import time
    return time.time()


def _get_db():
    from api.database import get_db
    return get_db()


def _session_repo(db):
    from repository.session_repo import SessionRepository
    return SessionRepository(db)


def create_session(user_id: str | None = None) -> dict[str, Any]:
    with _get_db() as db:
        repo = _session_repo(db)
        session = repo.create(user_id=user_id)
        return repo.to_dict(session)


def get_session(session_id: str) -> dict[str, Any] | None:
    session_id = (session_id or "").strip()
    if not session_id:
        return None
    with _get_db() as db:
        repo = _session_repo(db)
        session = repo.get(session_id)
        if session is None:
            return None
        return repo.to_dict(session)


def save_session(session: dict[str, Any]) -> dict[str, Any]:
    session_id = str(session.get("session_id") or "").strip()
    if not session_id:
        raise ValueError("session_id is required")
    with _get_db() as db:
        repo = _session_repo(db)
        db_session = repo.from_dict(session)
        return repo.to_dict(db_session)


def list_sessions(user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with _get_db() as db:
        repo = _session_repo(db)
        sessions = repo.list_by_user(user_id=user_id, limit=limit)
        return [repo.to_dict(s) for s in sessions]


def ensure_session(session_id: str | None, *, user_id: str | None = None) -> dict[str, Any]:
    if session_id:
        existing = get_session(session_id)
        if existing is not None:
            if user_id and not existing.get("user_id"):
                existing["user_id"] = user_id
                save_session(existing)
            return existing
    return create_session(user_id=user_id)
