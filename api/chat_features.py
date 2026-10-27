from __future__ import annotations

from typing import Any

from api.schemas.session import SessionDetail, SessionMessage, SessionSummary


def _normalize_line(text: str) -> str:
    return " ".join((text or "").strip().split())


def _truncate(text: str, *, limit: int) -> str:
    clean = _normalize_line(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def build_session_title(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if str(message.get("role") or "").strip().lower() == "user":
            content = _normalize_line(str(message.get("content") or ""))
            if content:
                return _truncate(content, limit=72)
    return "Nouvelle analyse"


def build_session_preview(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        content = _normalize_line(str(message.get("content") or ""))
        if content:
            return _truncate(content, limit=120)
    return ""


def build_session_summary(session: dict[str, Any]) -> SessionSummary:
    messages = list(session.get("messages") or [])
    return SessionSummary(
        session_id=str(session.get("session_id") or ""),
        user_id=str(session.get("user_id") or "") or None,
        title=build_session_title(messages),
        preview=build_session_preview(messages),
        updated_at=float(session.get("updated_at") or 0.0),
        message_count=len(messages),
    )


def build_session_detail(session: dict[str, Any]) -> SessionDetail:
    messages = [
        SessionMessage(
            role=str(message.get("role") or ""),
            content=str(message.get("content") or ""),
            ts=float(message.get("ts") or 0.0),
        )
        for message in list(session.get("messages") or [])
    ]
    summary = build_session_summary(session)
    return SessionDetail(
        session_id=summary.session_id,
        user_id=summary.user_id,
        title=summary.title,
        preview=summary.preview,
        updated_at=summary.updated_at,
        message_count=summary.message_count,
        messages=messages,
    )


def build_follow_up_suggestions(
    *,
    question: str,
    results: list[dict[str, Any]] | None,
    cypher: str,
    trace: list[dict[str, Any]] | None,
) -> list[str]:
    current_question = _normalize_line(question)
    rows = list(results or [])
    columns = [str(key) for key in (rows[0].keys() if rows else [])]
    lower_columns = [column.lower() for column in columns]
    trace_steps = list(trace or [])
    had_retry = any(str(step.get("node") or "") == "cypher_validator" for step in trace_steps) and any(
        str(step.get("event") or "") == "invalid" for step in trace_steps
    )

    suggestions: list[str] = []

    if rows:
        suggestions.append("Explique les tendances principales observees dans ces resultats.")

    date_column = next(
        (
            column
            for column in columns
            if "date" in column.lower() or "created" in column.lower() or "updated" in column.lower()
        ),
        "",
    )
    if date_column:
        suggestions.append(f"Montre uniquement les 10 lignes les plus recentes selon {date_column}.")

    if columns:
        suggestions.append(f"Donne une repartition agregee par {columns[0]}.")

    if len(columns) >= 2:
        suggestions.append(f"Analyse la relation entre {columns[0]} et {columns[1]}.")

    if "patient" in lower_columns or "patient" in current_question.lower():
        suggestions.append("Isole les patients qui apparaissent plusieurs fois dans ces resultats.")

    if "doctor" in lower_columns or "medecin" in current_question.lower():
        suggestions.append("Classe les medecins par volume d'activite sur cette selection.")

    if not rows:
        suggestions.append("Elargis la recherche avec des filtres plus souples pour retrouver des cas proches.")

    if "limit" in cypher.lower():
        suggestions.append("Supprime la limite actuelle pour voir si la tendance reste stable sur un volume plus large.")

    if had_retry:
        suggestions.append("Explique pourquoi la requete a necessite une correction avant execution.")

    suggestions.append("Transforme ces resultats en vue graphe pour montrer les relations cles.")

    deduped: list[str] = []
    seen: set[str] = set()
    for suggestion in suggestions:
        cleaned = _normalize_line(suggestion)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(cleaned)
        if len(deduped) == 5:
            break
    return deduped
