"""CRUD operations for chat sessions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from models.message import Message
from models.session import Session


class SessionRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def create(self, user_id: str | None = None) -> Session:
        session = Session(user_id=user_id)
        self.db.add(session)
        self.db.flush()
        return session

    def get(self, session_id: str) -> Session | None:
        return self.db.query(Session).filter(Session.id == session_id).first()

    def save(self, db_session: Session) -> Session:
        db_session.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return db_session

    def list_by_user(self, user_id: str | None = None, limit: int = 50) -> list[Session]:
        q = self.db.query(Session)
        if user_id:
            q = q.filter(Session.user_id == user_id)
        return q.order_by(Session.updated_at.desc()).limit(limit).all()

    def delete(self, session_id: str) -> bool:
        db_session = self.get(session_id)
        if db_session is None:
            return False
        self.db.delete(db_session)
        self.db.flush()
        return True

    def to_dict(self, db_session: Session) -> dict[str, Any]:
        return {
            "session_id": db_session.id,
            "user_id": db_session.user_id,
            "title": db_session.title or "",
            "created_at": db_session.created_at.timestamp() if db_session.created_at else 0.0,
            "updated_at": db_session.updated_at.timestamp() if db_session.updated_at else 0.0,
            "cancelled": db_session.cancelled,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "ts": m.created_at.timestamp() if m.created_at else 0.0,
                }
                for m in (db_session.messages or [])
            ],
        }

    def from_dict(self, data: dict[str, Any]) -> Session:
        db_session = self.get(data.get("session_id", ""))
        if db_session is None:
            db_session = Session(
                id=data.get("session_id", ""),
                user_id=data.get("user_id"),
                title=data.get("title", ""),
                cancelled=bool(data.get("cancelled", False)),
            )
            self.db.add(db_session)
        else:
            db_session.user_id = data.get("user_id") or db_session.user_id
            db_session.title = data.get("title", "") or db_session.title
            db_session.cancelled = bool(data.get("cancelled", db_session.cancelled))
        db_session.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return db_session
