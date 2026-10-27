from typing import Any, Iterator, Protocol


class LLMProvider(Protocol):
    def generate_cypher(
        self,
        *,
        system_prompt: str,
        question: str,
        cypher_draft: str | None = None,
        validation_error: str | None = None,
    ) -> str:
        """Generate a Cypher query from user question and context."""

    def synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> str:
        """Generate the final natural language answer from graph results."""

    def synthesize_genui_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> dict[str, Any]:
        """Generate a structured GenUI response (JSON with answer + blocks)."""

    def stream_synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> Iterator[str]:
        """Stream the final natural language answer token by token."""

    def chat(
        self,
        *,
        system_prompt: str,
        user_content: str,
        purpose: str = "chat",
    ) -> str:
        """Generate a short free-form completion (e.g. a conversation title)."""
