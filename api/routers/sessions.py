from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from api.chat_features import build_session_detail, build_session_summary
from api.middleware.auth import get_request_auth_context
from api.schemas.session import SessionDetail, SessionMessage, SessionSummary
from memory import session_manager as memory


class TitleUpdate(BaseModel):
    title: str

router = APIRouter(prefix="/sessions")


@router.get("/", response_model=list[SessionSummary])
def list_sessions(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> list[SessionSummary]:
    auth = get_request_auth_context(request)
    user_id = auth.get("user_id")
    sessions = memory.list_sessions(user_id=user_id, limit=limit)
    return [build_session_summary(s) for s in sessions]


@router.get("/{session_id}", response_model=SessionDetail)
def get_session_detail(session_id: str, request: Request) -> SessionDetail:
    session = memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    auth_context = get_request_auth_context(request)
    session_user_id = str(session.get("user_id") or "") or None
    requester_user_id = auth_context.get("user_id")
    requester_roles = [str(role) for role in auth_context.get("roles") or []]

    if session_user_id and requester_user_id and session_user_id != requester_user_id and "admin" not in requester_roles:
        raise HTTPException(status_code=403, detail="You cannot access this session.")

    return build_session_detail(session)


@router.put("/{session_id}/messages")
def update_session_messages(session_id: str, messages: list[SessionMessage], request: Request):
    session = memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    auth_context = get_request_auth_context(request)
    session_user_id = str(session.get("user_id") or "") or None
    requester_user_id = auth_context.get("user_id")
    requester_roles = [str(role) for role in auth_context.get("roles") or []]

    if session_user_id and requester_user_id and session_user_id != requester_user_id and "admin" not in requester_roles:
        raise HTTPException(status_code=403, detail="You cannot access this session.")

    from api.database import get_db
    from repository.message_repo import MessageRepository
    with get_db() as db:
        repo = MessageRepository(db)
        repo.delete_by_session(session_id)
        for m in messages:
            d = m.model_dump()
            repo.create(session_id=session_id, role=d.get("role", ""), content=d.get("content", ""))
    memory.save_session(session)
    return {"status": "success", "message_count": len(messages)}


@router.put("/{session_id}/title")
def update_session_title(session_id: str, body: TitleUpdate, request: Request):
    session = memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    auth_context = get_request_auth_context(request)
    session_user_id = str(session.get("user_id") or "") or None
    requester_user_id = auth_context.get("user_id")
    requester_roles = [str(role) for role in auth_context.get("roles") or []]

    if session_user_id and requester_user_id and session_user_id != requester_user_id and "admin" not in requester_roles:
        raise HTTPException(status_code=403, detail="You cannot modify this session.")

    session["title"] = body.title.strip() or session.get("title", "")
    memory.save_session(session)
    return {"status": "success", "title": session["title"]}


@router.delete("/{session_id}")
def delete_session(session_id: str, request: Request):
    session = memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    auth_context = get_request_auth_context(request)
    session_user_id = str(session.get("user_id") or "") or None
    requester_user_id = auth_context.get("user_id")
    requester_roles = [str(role) for role in auth_context.get("roles") or []]

    if session_user_id and requester_user_id and session_user_id != requester_user_id and "admin" not in requester_roles:
        raise HTTPException(status_code=403, detail="You cannot delete this session.")

    from api.database import get_db
    from repository.session_repo import SessionRepository
    with get_db() as db:
        repo = SessionRepository(db)
        repo.delete(session_id)

    return {"status": "success", "session_id": session_id}


@router.delete("/{session_id}/messages/{message_id}")
def delete_message(session_id: str, message_id: int, request: Request):
    session = memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    auth_context = get_request_auth_context(request)
    session_user_id = str(session.get("user_id") or "") or None
    requester_user_id = auth_context.get("user_id")
    requester_roles = [str(role) for role in auth_context.get("roles") or []]

    if session_user_id and requester_user_id and session_user_id != requester_user_id and "admin" not in requester_roles:
        raise HTTPException(status_code=403, detail="You cannot modify this session.")

    from api.database import get_db
    from repository.message_repo import MessageRepository
    with get_db() as db:
        repo = MessageRepository(db)
        deleted = repo.delete_by_session(session_id, after_id=message_id)

    return {"status": "success", "deleted_count": deleted}


@router.post("/{session_id}/cancel")
def cancel_session_execution(session_id: str, request: Request):
    session = memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    auth_context = get_request_auth_context(request)
    session_user_id = str(session.get("user_id") or "") or None
    requester_user_id = auth_context.get("user_id")
    requester_roles = [str(role) for role in auth_context.get("roles") or []]

    if session_user_id and requester_user_id and session_user_id != requester_user_id and "admin" not in requester_roles:
        raise HTTPException(status_code=403, detail="You cannot access this session.")

    session["cancelled"] = True
    memory.save_session(session)
    return {"status": "cancelled"}

