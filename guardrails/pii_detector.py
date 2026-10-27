"""Regex-first PII detection and redaction for chat inputs."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?(?:216|33|32|212)\s?)?(?:\d[\s.-]?){8,11}(?!\d)"
)
_INSEE_RE = re.compile(r"\b[12]\d{12,14}\b")

# Ajout : INAMI belge (11 chiffres)
_INAMI_RE = re.compile(r"\b\d{11}\b")

# Ajout : dates de naissance
_BIRTHDATE_RE = re.compile(
    r"\b(?:n[ée]e?\s+le|ddn|date\s+de\s+naissance)\s*:?\s*"
    r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b",
    re.IGNORECASE,
)

_POLICY_ID_RE = re.compile(
    r"\b(?:policy|police|contrat|adherent|adh[ée]rent|matricule|assure)\s*"
    r"[:#-]?\s*([A-Z0-9-]{6,})\b",
    re.IGNORECASE,
)

# Require a real separator after the keyword so "nombre" is not parsed as
# "nom" followed by a fake person name.
#
# IMPORTANT: do NOT use IGNORECASE for the full regex. Otherwise `[A-Z]` also
# matches lowercase letters and will incorrectly redact phrases like
# "assuré en moyenne" as if "en" was a person name.
_PERSON_AFTER_KEYWORD_RE = re.compile(
    r"\b(?P<prefix>(?i:patient|assur[ée]|doctor|docteur|m[ée]decin|nom|name))\b"
    r"(?:\s*[:=-]\s*|\s+)"
    r"(?P<value>[A-Z][A-Za-zÀ-ÿ'\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ'\-]+){0,2})"
)


def _replace_pattern(
    text: str,
    pattern: re.Pattern[str],
    label: str,
    redactions: list[dict[str, Any]],
) -> str:
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        placeholder = f"<{label}_{counter}>"
        redactions.append(
            {
                "type": label.lower(),
                "placeholder": placeholder,
                "start": match.start(),
                "end": match.end(),
            }
        )
        logger.debug(
            "PII redacted: type=%s offset=%d-%d",
            label,
            match.start(),
            match.end(),
        )
        return placeholder

    return pattern.sub(repl, text)


def _replace_policy_ids(text: str, redactions: list[dict[str, Any]]) -> str:
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        placeholder = f"<POLICY_ID_{counter}>"
        redactions.append(
            {
                "type": "policy_id",
                "placeholder": placeholder,
                "start": match.start(1),
                "end": match.end(1),
            }
        )
        return match.group(0).replace(match.group(1), placeholder)

    return _POLICY_ID_RE.sub(repl, text)


def _replace_names_after_keywords(
    text: str, redactions: list[dict[str, Any]]
) -> str:
    counter = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        placeholder = f"<PERSON_{counter}>"
        redactions.append(
            {
                "type": "person_name",
                "placeholder": placeholder,
                "start": match.start("value"),
                "end": match.end("value"),
            }
        )
        return f"{match.group('prefix')} {placeholder}"

    return _PERSON_AFTER_KEYWORD_RE.sub(repl, text)


def detect_and_redact_pii(text: str) -> tuple[str, list[dict[str, Any]]]:
    if not text or not text.strip():
        return text, []

    redactions: list[dict[str, Any]] = []
    out = text

    # Ordre important : identifiants forts d'abord
    out = _replace_pattern(out, _EMAIL_RE, "EMAIL", redactions)
    out = _replace_pattern(out, _INSEE_RE, "INSEE", redactions)
    out = _replace_pattern(out, _INAMI_RE, "INAMI", redactions)
    out = _replace_pattern(out, _BIRTHDATE_RE, "BIRTHDATE", redactions)
    out = _replace_policy_ids(out, redactions)
    out = _replace_names_after_keywords(out, redactions)
    out = _replace_pattern(out, _PHONE_RE, "PHONE", redactions)

    if redactions:
        logger.info("PII detected and redacted: %d entities", len(redactions))

    return out, redactions


def redact_pii(text: str) -> str:
    return detect_and_redact_pii(text)[0]
