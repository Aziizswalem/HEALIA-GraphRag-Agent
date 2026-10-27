from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ChatResponse(BaseModel):
    """Natural-language answer is separate from generated Cypher and execution trace."""

    answer: str
    cypher: str = ""
    trace_id: str = ""
    session_id: str = ""
    results: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    genui_blocks: list[dict[str, Any]] = Field(default_factory=list)


class StreamChunk(BaseModel):
    type: str
    node: str = ""
    token: str = ""
    answer: str = ""
    cypher: str = ""
    trace_id: str = ""
    results: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    step: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    validation_error: str = ""
    warning: str = ""
    session_id: str = ""
    genui_blocks: list[dict[str, Any]] = Field(default_factory=list)
