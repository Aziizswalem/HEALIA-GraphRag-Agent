"""Last-N conversation turns stored in PostgreSQL (via SQLAlchemy)."""
from __future__ import annotations

from typing import Any

from config.settings import get_settings


def _get_db():
    from api.database import get_db
    return get_db()


def _msg_repo(db):
    from repository.message_repo import MessageRepository
    return MessageRepository(db)


def _session_repo(db):
    from repository.session_repo import SessionRepository
    return SessionRepository(db)


def _trim_to_limit(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_turns = int(get_settings().CONVERSATION_MAX_TURNS)
    if max_turns <= 0:
        return []
    if len(messages) <= max_turns:
        return messages
    return messages[-max_turns:]


def append_turn(session_id: str, role: str, content: str, *, cypher: str | None = None) -> None:
    if not get_settings().CONVERSATION_MEMORY_ENABLED:
        return
    role = (role or "").strip()
    content = (content or "").strip()
    if not role or not content:
        return
    with _get_db() as db:
        msg_repo = _msg_repo(db)
        msg_repo.create(session_id=session_id, role=role, content=content, cypher=cypher)
        session_repo = _session_repo(db)
        session = session_repo.get(session_id)
        if session:
            session_repo.save(session)


def get_recent_turns(session_id: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    if not get_settings().CONVERSATION_MEMORY_ENABLED:
        return []
    if limit is None:
        limit = int(get_settings().CONVERSATION_CONTEXT_TURNS)
    if limit <= 0:
        return []
    with _get_db() as db:
        repo = _msg_repo(db)
        messages = repo.get_recent(session_id, limit=limit)
        turns = [repo.to_dict(m) for m in reversed(messages)]
    return _trim_to_limit(turns)


def build_context_prompt(session_id: str, message: str) -> str:
    from memory.context_builder import build_context
    return build_context(session_id, message)
