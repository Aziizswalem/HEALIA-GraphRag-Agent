"""Route generation tasks to the configured LLM provider."""
from __future__ import annotations

from config.settings import get_settings
from llm.providers.base import LLMProvider


def normalize_provider_name(provider_name: str) -> str:
    normalized = provider_name.strip().lower()
    if normalized in {"openai_compatible", "gpu_cloud"}:
        return "openai_compatible"
    if normalized in {"anthropic", "groq", "openai"}:
        return normalized
    raise ValueError(
        "Unsupported LLM_PROVIDER. Expected one of: "
        "'groq', 'openai', 'openai_compatible', 'gpu_cloud', 'anthropic'."
    )


class DemoMockProvider:
    """Mock LLM provider for DEMO_MODE that performs 0 network requests."""

    def generate_cypher(
        self,
        *,
        system_prompt: str,
        question: str,
        cypher_draft: str | None = None,
        validation_error: str | None = None,
    ) -> str:
        return ""

    def synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> str:
        return "Mode démo autonome actif."

    def synthesize_genui_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> dict:
        return {"answer": "Mode démo autonome actif.", "blocks": []}

    def stream_synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ):
        yield "Mode démo autonome actif."

    def chat(
        self,
        *,
        system_prompt: str,
        user_content: str,
        purpose: str = "chat",
    ) -> str:
        return user_content.strip()[:60] or "Nouvelle analyse"


def get_provider() -> LLMProvider:
    s = get_settings()
    if getattr(s, "DEMO_MODE", False):
        return DemoMockProvider()  # type: ignore[return-value]

    provider = normalize_provider_name(s.LLM_PROVIDER)
    if provider == "anthropic":
        from llm.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if provider == "openai":
        from llm.providers.openai import OpenAIProvider

        return OpenAIProvider(provider_label="openai")
    if provider == "openai_compatible":
        from llm.providers.openai import OpenAIProvider

        return OpenAIProvider(provider_label="openai_compatible", require_base_url=True)
    from llm.providers.groq import GroqProvider

    return GroqProvider()

