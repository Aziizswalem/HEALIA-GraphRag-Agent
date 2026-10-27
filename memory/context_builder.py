"""Build LLM context prompt with token budget."""
from __future__ import annotations

from typing import Any

from config.settings import get_settings
from memory.conversation_buffer import get_recent_turns


def _estimate_tokens(text: str) -> int:
    return len((text or "").split())


def build_context(session_id: str, message: str) -> str:
    current = (message or "").strip()
    turns = list(get_recent_turns(session_id))

    if not turns:
        return current

    s = get_settings()
    budget = int(s.CONTEXT_TOKEN_BUDGET)
    max_turns = int(s.MAX_HISTORY_TURNS)

    lines: list[str] = ["Conversation history:"]
    token_count = 0
    selected = 0

    for turn in reversed(turns[-max_turns:]):
        role = str(turn.get("role") or "user").strip().lower()
        label = "User" if role == "user" else "Assistant"
        text = str(turn.get("content") or "")
        line = f"{label}: {text}"
        tokens = _estimate_tokens(line) + 1
        if token_count + tokens > budget:
            break
        lines.insert(1, line)
        token_count += tokens
        selected += 1

    if selected == 0:
        return current

    lines.append("")
    lines.append("Current user question:")
    lines.append(current)
    return "\n".join(lines).strip()
