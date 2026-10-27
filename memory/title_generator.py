"""Generate a short conversation title from the user's first message using the configured LLM."""
from __future__ import annotations

from llm.router import get_provider

TITLE_SYSTEM_PROMPT = (
    "Generate a very short title (3 to 6 words) that summarizes the user's question. "
    "The title must be in the same language as the question (French or English). "
    "Output ONLY the title — no quotes, no punctuation, no explanation."
)


def generate_title(user_message: str) -> str:
    """Generate an LLM title from the question; fall back to the question itself."""
    from config.settings import get_settings
    if getattr(get_settings(), "DEMO_MODE", False):
        return _fallback_title(user_message)
    try:
        provider = get_provider()
        title = provider.chat(
            system_prompt=TITLE_SYSTEM_PROMPT,
            user_content=(user_message or "").strip(),
            purpose="title_generation",
        )
        title = (title or "").strip().strip("\"'.,!?;:-").strip()
        return title or _fallback_title(user_message)
    except Exception:
        return _fallback_title(user_message)


def _fallback_title(user_message: str) -> str:
    words = (user_message or "").strip().split()
    if not words:
        return "Nouvelle analyse"
    title = " ".join(words[:8])
    if len(title) > 72:
        title = title[:69] + "..."
    return title
