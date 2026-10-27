from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from starlette.websockets import WebSocketState

from agent.graph import run_agent, run_agent_stream
from api.chat_features import build_follow_up_suggestions
from api.middleware.auth import get_request_auth_context
from api.schemas.chat import ChatRequest, ChatResponse
from config.settings import get_settings
from guardrails.pii_detector import detect_and_redact_pii
from memory.conversation_buffer import append_turn, build_context_prompt
from memory.session_manager import ensure_session, save_session
from memory.title_generator import generate_title
from observability.prometheus_metrics import inc_chat_requests

router = APIRouter()


class TitleRequest(BaseModel):
    message: str


@router.post("/chat/title")
def chat_title(body: TitleRequest):
    """Generate an LLM title for a message without creating a session."""
    return {"title": generate_title(body.message)}


def _sanitize_ws_message(message: str) -> tuple[str, list[dict[str, str]]]:
    settings = get_settings()
    if not settings.PII_FILTER_ENABLED:
        return message, []
    return detect_and_redact_pii(message)


def _resolve_http_session_id(request: Request, body_session_id: str | None) -> str | None:
    candidate = (body_session_id or "").strip()
    if candidate:
        return candidate
    header_candidate = (request.headers.get("X-Session-Id") or "").strip()
    if header_candidate:
        return header_candidate
    cookie_name = get_settings().SESSION_COOKIE_NAME
    return (request.cookies.get(cookie_name) or "").strip() or None


def _resolve_ws_session_id(ws: WebSocket, payload_session_id: str | None, current_session_id: str) -> str | None:
    candidate = (payload_session_id or "").strip()
    if candidate:
        return candidate
    if current_session_id.strip():
        return current_session_id.strip()
    header_candidate = (ws.headers.get("X-Session-Id") or "").strip()
    if header_candidate:
        return header_candidate
    cookie_name = get_settings().SESSION_COOKIE_NAME
    cookie_candidate = (ws.cookies.get(cookie_name) or "").strip()
    if cookie_candidate:
        return cookie_candidate
    query_candidate = (ws.query_params.get("session_id") or "").strip()
    return query_candidate or None


async def _iterate_sync_events(
    events: Iterator[dict[str, Any]],
) -> AsyncIterator[dict[str, Any]]:
    sentinel = object()
    while True:
        event = await asyncio.to_thread(next, events, sentinel)
        if event is sentinel:
            return
        yield event


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request, response: Response):
    auth_context = get_request_auth_context(request)
    resolved_session_id = _resolve_http_session_id(request, req.session_id)
    session = ensure_session(
        resolved_session_id,
        user_id=auth_context.get("user_id"),
    )
    session_id = session["session_id"]
    if session.get("cancelled"):
        session["cancelled"] = False
        save_session(session)

    agent_question = build_context_prompt(session_id, req.message)

    inc_chat_requests("/chat", "sync")
    try:
        out = run_agent(
            agent_question,
            user_id=auth_context.get("user_id"),
            session_id=session_id,
            metadata={"transport": "http", "route": "/chat"},
            tags=["chat", "sync"],
        )
    except Exception as exc:
        if "cancelled by user" in str(exc):
            return ChatResponse(
                answer="Query execution was cancelled.",
                session_id=session_id,
            )
        raise exc

    answer = out.get("answer") or ""
    results = list(out.get("results") or [])
    trace = list(out.get("trace") or [])
    suggestions = build_follow_up_suggestions(
        question=req.message,
        results=results,
        cypher=str(out.get("cypher") or ""),
        trace=trace,
    )

    append_turn(session_id, "user", req.message)
    append_turn(session_id, "assistant", answer, cypher=out.get("cypher") or "")

    if not session.get("title"):
        _generate_and_save_title(session, req.message)

    settings = get_settings()
    response.headers["X-Session-Id"] = session_id
    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        samesite="lax",
        max_age=int(settings.SESSION_TTL_SECONDS),
    )

    return ChatResponse(
        answer=answer,
        cypher=out.get("cypher") or "",
        trace_id=out.get("trace_id") or "",
        session_id=session_id,
        results=results,
        suggestions=suggestions,
        trace=trace,
        metrics=dict(out.get("metrics") or {}),
        genui_blocks=list(out.get("genui_blocks") or []),
    )


def _generate_and_save_title(session: dict, user_message: str) -> None:
    try:
        title = generate_title(user_message)
        session["title"] = title
        save_session(session)
    except Exception:
        pass


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    current_session_id = ""
    try:
        while True:
            final_answer = ""
            sanitized_message = ""
            payload = await ws.receive_json()
            req = ChatRequest(**payload)
            sanitized_message, redactions = _sanitize_ws_message(req.message)
            resolved_session_id = _resolve_ws_session_id(ws, req.session_id, current_session_id)
            session = ensure_session(resolved_session_id)
            current_session_id = session["session_id"]
            if session.get("cancelled"):
                session["cancelled"] = False
                save_session(session)
            agent_question = build_context_prompt(current_session_id, sanitized_message)

            inc_chat_requests("/ws/chat", "stream")
            stream = run_agent_stream(
                agent_question,
                pii_redactions=redactions,
                session_id=current_session_id,
                user_id=None,
                metadata={"transport": "websocket", "route": "/ws/chat"},
                tags=["chat", "stream"],
            )
            async for event in _iterate_sync_events(stream):
                if event.get("type") == "start":
                    event = dict(event)
                    event["question"] = sanitized_message
                    event["session_id"] = current_session_id
                if event.get("type") == "final":
                    final_answer = str(event.get("answer") or "")
                    event = dict(event)
                    event["session_id"] = current_session_id
                    event["suggestions"] = build_follow_up_suggestions(
                        question=sanitized_message,
                        results=list(event.get("results") or []),
                        cypher=str(event.get("cypher") or ""),
                        trace=list(event.get("trace") or []),
                    )
                await ws.send_json(event)

            if sanitized_message and final_answer:
                append_turn(current_session_id, "user", sanitized_message)
                append_turn(current_session_id, "assistant", final_answer)
    except ValidationError as exc:
        await ws.send_json({"type": "error", "error": f"Invalid request: {exc}"})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await ws.send_json({"type": "error", "error": str(exc)})
    finally:
        if ws.client_state != WebSocketState.DISCONNECTED:
            await ws.close()
