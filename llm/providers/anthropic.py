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


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        from anthropic import Anthropic

        s = get_settings()
        self.client = Anthropic(api_key=s.ANTHROPIC_API_KEY)
        self.model = s.ANTHROPIC_MODEL

    def generate_cypher(
        self,
        *,
        system_prompt: str,
        question: str,
        cypher_draft: str | None = None,
        validation_error: str | None = None,
    ) -> str:
        messages = [{"role": "user", "content": question}]
        if validation_error and cypher_draft:
            messages = [
                {
                    "role": "user",
                    "content": (
                        f"Original question: {question}\n\n"
                        f"Failed query:\n{cypher_draft}\n\n"
                        f"Error: {validation_error}\n\n"
                        "Generate a corrected query."
                    ),
                }
            ]
        with start_observation(
            name="anthropic.messages.create",
            as_type="generation",
            input_payload={
                "system_prompt": system_prompt,
                "messages": messages,
            },
            model=self.model,
            model_parameters={"max_tokens": 1024},
            metadata={"provider": "anthropic", "purpose": "generate_cypher"},
        ) as generation:
            t0 = time.perf_counter()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )
            ttft_ms = (time.perf_counter() - t0) * 1000
            record_ttft(ttft_ms, purpose="generate_cypher")
            output = response.content[0].text.strip()
            usage = getattr(response, "usage", None)
            usage_details: dict[str, int] | None = None
            if usage is not None:
                usage_details = {
                    "prompt_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                }
                usage_details["total_tokens"] = (
                    usage_details["prompt_tokens"] + usage_details["completion_tokens"]
                )
            generation.update(output=output, usage_details=usage_details)
            record_llm_call(
                provider="anthropic",
                model=self.model,
                purpose="generate_cypher",
                usage_details=usage_details,
            )
            return output

    def synthesize_genui_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> dict[str, Any]:
        user_content = f"User question: {question}\n\n{data_payload}"
        json_prompt = (
            "You MUST respond with a valid JSON object containing 'answer' (string) and 'blocks' (array). "
            "No other text, no formatting, no markdown. Only a raw JSON object."
        )
        combined_prompt = f"{system_prompt}\n\n{json_prompt}"
        with start_observation(
            name="anthropic.messages.create",
            as_type="generation",
            input_payload={
                "system_prompt": combined_prompt,
                "user_content": user_content,
            },
            model=self.model,
            model_parameters={"max_tokens": 2048},
            metadata={"provider": "anthropic", "purpose": "synthesize_genui"},
        ) as generation:
            t0 = time.perf_counter()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=combined_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            ttft_ms = (time.perf_counter() - t0) * 1000
            record_ttft(ttft_ms, purpose="synthesize_genui")
            output = response.content[0].text.strip()
            usage = getattr(response, "usage", None)
            usage_details: dict[str, int] | None = None
            if usage is not None:
                usage_details = {
                    "prompt_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                }
                usage_details["total_tokens"] = (
                    usage_details["prompt_tokens"] + usage_details["completion_tokens"]
                )
            generation.update(output=output, usage_details=usage_details)
            record_llm_call(
                provider="anthropic",
                model=self.model,
                purpose="synthesize_genui",
                usage_details=usage_details,
            )
            try:
                # Strip markdown code fences if present
                cleaned = output.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    cleaned = "\n".join(lines[1:] if lines[0].startswith("```") else lines)
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3].strip()
                return json.loads(cleaned)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Anthropic JSON parse failed: %s", exc)
                return {"answer": output, "blocks": []}

    def synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> str:
        user_content = f"User question: {question}\n\n{data_payload}"
        with start_observation(
            name="anthropic.messages.create",
            as_type="generation",
            input_payload={
                "system_prompt": system_prompt,
                "user_content": user_content,
            },
            model=self.model,
            model_parameters={"max_tokens": 1024},
            metadata={"provider": "anthropic", "purpose": "synthesize_answer"},
        ) as generation:
            t0 = time.perf_counter()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_content,
                    }
                ],
            )
            ttft_ms = (time.perf_counter() - t0) * 1000
            record_ttft(ttft_ms, purpose="synthesize_answer")
            output = response.content[0].text.strip()
            usage = getattr(response, "usage", None)
            usage_details: dict[str, int] | None = None
            if usage is not None:
                usage_details = {
                    "prompt_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                }
                usage_details["total_tokens"] = (
                    usage_details["prompt_tokens"] + usage_details["completion_tokens"]
                )
            generation.update(output=output, usage_details=usage_details)
            record_llm_call(
                provider="anthropic",
                model=self.model,
                purpose="synthesize_answer",
                usage_details=usage_details,
            )
            return output

    def stream_synthesize_answer(
        self,
        *,
        system_prompt: str,
        question: str,
        data_payload: str,
    ) -> Iterator[str]:
        user_content = f"User question: {question}\n\n{data_payload}"
        with start_observation(
            name="anthropic.messages.stream",
            as_type="generation",
            input_payload={
                "system_prompt": system_prompt,
                "user_content": user_content,
            },
            model=self.model,
            model_parameters={"max_tokens": 1024, "stream": True},
            metadata={"provider": "anthropic", "purpose": "stream_synthesize_answer"},
        ) as generation:
            chunks: list[str] = []
            usage_details: dict[str, int] | None = None
            t0 = time.perf_counter()
            first_token_recorded = False
            with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_content,
                    }
                ],
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        if not first_token_recorded:
                            ttft_ms = (time.perf_counter() - t0) * 1000
                            record_ttft(ttft_ms, purpose="stream_synthesize")
                            first_token_recorded = True
                        chunks.append(text)
                        yield text
                final_message = stream.get_final_message()
                usage = getattr(final_message, "usage", None)
                if usage is not None:
                    usage_details = {
                        "prompt_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                        "completion_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                    }
                    usage_details["total_tokens"] = (
                        usage_details["prompt_tokens"] + usage_details["completion_tokens"]
                    )
            generation.update(
                output="".join(chunks).strip(),
                usage_details=usage_details,
            )
            record_llm_call(
                provider="anthropic",
                model=self.model,
                purpose="stream_synthesize_answer",
                usage_details=usage_details,
            )

    def chat(
        self,
        *,
        system_prompt: str,
        user_content: str,
        purpose: str = "chat",
    ) -> str:
        with start_observation(
            name="anthropic.messages.create",
            as_type="generation",
            input_payload={
                "system_prompt": system_prompt,
                "user_content": user_content,
            },
            model=self.model,
            model_parameters={"max_tokens": 30},
            metadata={"provider": "anthropic", "purpose": purpose},
        ) as generation:
            t0 = time.perf_counter()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=30,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            ttft_ms = (time.perf_counter() - t0) * 1000
            record_ttft(ttft_ms, purpose=purpose)
            output = response.content[0].text.strip()
            usage = getattr(response, "usage", None)
            usage_details: dict[str, int] | None = None
            if usage is not None:
                usage_details = {
                    "prompt_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage, "output_tokens", 0) or 0),
                }
                usage_details["total_tokens"] = (
                    usage_details["prompt_tokens"] + usage_details["completion_tokens"]
                )
            generation.update(output=output, usage_details=usage_details)
            record_llm_call(
                provider="anthropic",
                model=self.model,
                purpose=purpose,
                usage_details=usage_details,
            )
            return output
