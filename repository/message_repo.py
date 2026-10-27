"""CRUD operations for chat messages."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from models.message import Message


class MessageRepository:
    def __init__(self, db: DBSession):
        self.db = db

    def create(self, session_id: str, role: str, content: str, *, cypher: str | None = None, token_count: int | None = None) -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            cypher=cypher,
            token_count=token_count,
        )
        self.db.add(msg)
        self.db.flush()
        return msg

    def get_recent(self, session_id: str, limit: int = 20) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_recent_since(self, session_id: str, since: datetime, limit: int = 20) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.session_id == session_id, Message.created_at >= since)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

    def list_by_session(self, session_id: str) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    def delete(self, message_id: int) -> bool:
        msg = self.db.query(Message).filter(Message.id == message_id).first()
        if msg is None:
            return False
        self.db.delete(msg)
        self.db.flush()
        return True

    def delete_by_session(self, session_id: str, after_id: int | None = None) -> int:
        q = self.db.query(Message).filter(Message.session_id == session_id)
        if after_id is not None:
            msg = self.db.query(Message).filter(Message.id == after_id).first()
            if msg:
                q = q.filter(Message.created_at >= msg.created_at)
        deleted = q.delete(synchronize_session="fetch")
        self.db.flush()
        return deleted

    def to_dict(self, msg: Message) -> dict[str, Any]:
        return {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "ts": msg.created_at.timestamp() if msg.created_at else 0.0,
        }
