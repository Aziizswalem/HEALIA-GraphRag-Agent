from typing import Any

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    user_id: str | None = None


class SessionMessage(BaseModel):
    role: str
    content: str
    ts: float = 0.0


class SessionSummary(BaseModel):
    session_id: str
    user_id: str | None = None
    title: str = ""
    preview: str = ""
    updated_at: float = 0.0
    message_count: int = 0


class SessionState(BaseModel):
    session_id: str
    user_id: str | None = None
    messages: list[dict[str, Any]] = Field(default_factory=list)


class SessionDetail(SessionSummary):
    messages: list[SessionMessage] = Field(default_factory=list)
