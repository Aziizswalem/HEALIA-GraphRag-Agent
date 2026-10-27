"""
Semantic plan validator — LLM-based judge.

Runs AFTER all syntactic and schema checks pass.
Asks the LLM whether the Cypher actually answers the user's question.

Design:
- Fail-open: any LLM failure returns None (does not block the query)
- Conservative: only blocks when confidence >= threshold (default 0.75)
- Lightweight: 512 max_tokens, structured JSON output
- Skips on retry >= 2 to avoid infinite loops
"""
from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_JUDGE_PROMPT = """\
You are a Cypher query semantic validator for a Neo4j graph database.

## Available schema
{schema_context}

## User question
{question}

## Generated Cypher
{cypher}

## Your task
Decide whether the Cypher query correctly answers the user question.

Check:
1. Does it target the right nodes / relationships for the question?
2. Does it apply the right filters (dates, identifiers, amounts, conditions)?
3. Does it return the right columns / aggregations?
4. Does it traverse the right graph paths (not shortcuts that skip required joins)?
5. Is the cardinality correct (LIMIT, aggregation logic)?

Respond ONLY with a JSON object — no markdown, no preamble:
{{
  "valid": <true|false>,
  "confidence": <float 0.0–1.0>,
  "issues": [<specific issue strings if invalid, empty list if valid>],
  "hint": "<one-sentence correction hint for the generator if invalid, empty string if valid>"
}}

Rules:
- Set "valid": true for minor style differences (alias names, property order, etc.)
- Only set "valid": false when you are confident (confidence > 0.75) the logic is wrong
- Do NOT flag missing ORDER BY or LIMIT unless the question explicitly requires them
- Focus on: wrong traversal path, missing or wrong filter, wrong aggregation, wrong RETURN
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def semantic_plan_check(
    question: str,
    cypher: str,
    schema_context: str,
    retry_count: int = 0,
    llm_client=None,
    model: str = "claude-sonnet-4-20250514",
    confidence_threshold: float = 0.75,
    max_tokens: int = 512,
) -> str | None:
    """
    Call the LLM to verify that `cypher` semantically answers `question`.

    Returns:
        None   — query is semantically valid (or the check could not run).
        str    — error message to feed back to the generator.

    Parameters:
        question            Natural language question from the user.
        cypher              The Cypher query to evaluate.
        schema_context      Schema string already built by the validator.
        retry_count         Current retry count. Skipped when >= 2 (avoids loops).
        llm_client          Anthropic client instance. Auto-created if None.
        model               Model to use.
        confidence_threshold Minimum confidence to reject a query (default 0.75).
        max_tokens          Upper bound on the judge's response.
    """
    # Guard: don't add latency on late retries
    if retry_count >= 2:
        logger.debug("semantic_plan_check: skipped (retry_count=%d >= 2)", retry_count)
        return None

    if not question or not cypher:
        return None

    client = _get_client(llm_client)
    if client is None:
        return None

    prompt = _JUDGE_PROMPT.format(
        schema_context=schema_context.strip(),
        question=question.strip(),
        cypher=cypher.strip(),
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
    except Exception as exc:
        logger.warning("semantic_plan_check: LLM call failed: %s", exc)
        return None  # fail-open

    result = _parse_judge_response(raw)
    if result is None:
        return None  # fail-open on parse error

    valid = result.get("valid", True)
    confidence = float(result.get("confidence", 0.0))
    issues = result.get("issues", [])
    hint = result.get("hint", "")

    if not valid and confidence >= confidence_threshold:
        parts = [f"Semantic validation failed (confidence={confidence:.2f})"]
        if issues:
            parts.append("; ".join(issues))
        if hint:
            parts.append(f"Hint: {hint}")
        return " | ".join(parts)

    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client(llm_client):
    if llm_client is not None:
        return llm_client
    try:
        import anthropic
        return anthropic.Anthropic()
    except Exception as exc:
        logger.warning("semantic_plan_check: cannot init Anthropic client: %s", exc)
        return None


def _parse_judge_response(raw: str) -> dict | None:
    """Strip markdown fences if present and parse JSON."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("semantic_plan_check: JSON parse error: %s — raw: %.200s", exc, raw)
        return None
