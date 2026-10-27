"""OpenAI Chat Completions for fallback and streaming synthesis."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Iterator

from config.settings import get_settings
from llm.providers.base import LLMProvider
from observability.langfuse_tracer import start_observation
from observability.run_metrics import record_llm_call, record_ttft

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        *,
        provider_label: str = "openai",
        require_base_url: bool = False,
    ) -> None:
        from openai import OpenAI

        s = get_settings()
        api_key = (s.OPENAI_API_KEY or "").strip()
        base_url = (s.OPENAI_BASE_URL or "").strip() or None

        if require_base_url and not base_url:
            raise ValueError(
                "OPENAI_BASE_URL is required when LLM_PROVIDER is "
                "'openai_compatible' or 'gpu_cloud'."
            )
        if not api_key:
            if base_url:
                api_key = "stagee-local"
            else:
                raise ValueError(
                    "OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'."
                )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=float(s.OPENAI_TIMEOUT_SECONDS),
            max_retries=int(s.OPENAI_MAX_RETRIES),
        )
        self.model = s.OPENAI_CHAT_MODEL
        self.provider_label = provider_label
        self._ollama_compatible = bool(base_url) and ("ollama" in base_url.lower() or ":11434" in base_url)

    def _chat(self, *, system_prompt: str, user_content: str, purpose: str, temperature: float = 0) -> str:
        with start_observation(
            name="openai.chat.completions",
            as_type="generation",
            input_payload={
                "system_prompt": system_prompt,
                "user_content": user_content,
            },
            model=self.model,
            model_parameters={"temperature": temperature},
            metadata={"provider": self.provider_label},
        ) as generation:
            t0 = time.perf_counter()
            extra = {"options": {"num_ctx": 16384}} if self._ollama_compatible else {}
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                extra_body=extra,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            ttft_ms = (time.perf_counter() - t0) * 1000
            record_ttft(ttft_ms, purpose=purpose)
            content = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            usage_details: dict[str, int] | None = None
            if usage is not None:
                usage_details = {
                    "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                    "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
                }
            generation.update(
                output=(content or "").strip(),
                usage_details=usage_details,
            )
            record_llm_call(
                provider=self.provider_label,
                model=self.model,
                purpose=purpose,
                usage_details=usage_details,
            )
            return (content or "").strip()

    def _chat_stream(
        self,
        *,
        system_prompt: str,
        user_content: str,
        purpose: str = "stream_synthesize",
    ) -> Iterator[str]:
        with start_observation(
            name="openai.chat.completions.stream",
            as_type="generation",
            input_payload={
                "system_prompt": system_prompt,
                "user_content": user_content,
            },
            model=self.model,
            model_parameters={"temperature": 0, "stream": True},
            metadata={"provider": self.provider_label},
        ) as generation:
            chunks: list[str] = []
            t0 = time.perf_counter()
            first_token_recorded = False
            stream = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                extra_body={"options": {"num_ctx": 16384}} if self._ollama_compatible else {},
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if isinstance(content, str) and content:
                    if not first_token_recorded:
                        ttft_ms = (time.perf_counter() - t0) * 1000
                        record_ttft(ttft_ms, purpose=purpose)
                        first_token_recorded = True
                    chunks.append(content)
                    yield content
            generation.update(output="".join(chunks).strip())

    def generate_cypher(
        self,
        *,
        system_prompt: str,
        question: str,
        cypher_draft: str | None = None,
        validation_error: str | None = None,
    ) -> str:
        is_retry = bool(validation_error and cypher_draft)
        if is_retry:
            user_content = (
                f"Original question: {question}\n\n"
                f"Failed query:\n{cypher_draft}\n\n"
                f"Error: {validation_error}\n\n"
                "Generate a corrected query."
            )
            temperature = 0.2
        else:
            user_content = question
            temperature = 0
        return self._chat(
            system_prompt=system_prompt,
            user_content=user_content,
            purpose="generate_cypher",
            temperature=temperature,
        )

    def _chat_json(self, *, system_prompt: str, user_content: str, purpose: str) -> dict[str, Any]:
        extra = {"options": {"num_ctx": 16384}} if self._ollama_compatible else {}
        with start_observation(
            name="openai.chat.completions.json",
            as_type="generation",
            input_payload={
                "system_prompt": system_prompt,
                "user_content": user_content,
            },
            model=self.model,
            model_parameters={"temperature": 0, "response_format": "json_object"},
            metadata={"provider": self.provider_label, "purpose": purpose},
        ) as generation:
            t0 = time.perf_counter()
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                extra_body=extra,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            ttft_ms = (time.perf_counter() - t0) * 1000
            record_ttft(ttft_ms, purpose=purpose)
            content = (response.choices[0].message.content or "").strip()
            usage = getattr(response, "usage", None)
            usage_details: dict[str, int] | None = None
            if usage is not None:
                usage_details = {
                    "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                    "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
                }
            generation.update(output=content, usage_details=usage_details)
            record_llm_call(
                provider=self.provider_label,
                model=self.model,
                purpose=purpose,
                usage_details=usage_details,
            )
            try:
                return json.loads(content)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("OpenAI JSON mode returned invalid JSON: %s", exc)
                return {}

    def synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> str:
        user_content = f"User question: {question}\n\n{data_payload}"
        return self._chat(
            system_prompt=system_prompt,
            user_content=user_content,
            purpose="synthesize_answer",
        )

    def synthesize_genui_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> dict[str, Any]:
        user_content = f"User question: {question}\n\n{data_payload}"
        return self._chat_json(
            system_prompt=system_prompt,
            user_content=user_content,
            purpose="synthesize_genui",
        )

    def stream_synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> Iterator[str]:
        user_content = f"User question: {question}\n\n{data_payload}"
        return self._chat_stream(
            system_prompt=system_prompt,
            user_content=user_content,
            purpose="stream_synthesize",
        )

    def chat(
        self,
        *,
        system_prompt: str,
        user_content: str,
        purpose: str = "chat",
    ) -> str:
        return self._chat(
            system_prompt=system_prompt,
            user_content=user_content,
            purpose=purpose,
            temperature=0.1,
        )
