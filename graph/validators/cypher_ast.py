"""
Lightweight local Cypher pre-validation.

This is not a full Cypher parser, but it catches many common LLM mistakes
before we hit Neo4j:
- empty queries
- unbalanced (), [], {}
- unterminated strings / identifiers / comments
- semicolons or multiple statements
- SQL-looking queries
- queries that do not contain a plausible Cypher clause
"""
from __future__ import annotations

import re

_CLAUSE_RE = re.compile(r"\b(OPTIONAL\s+MATCH|MATCH|WITH|RETURN|UNWIND|CALL)\b", re.IGNORECASE)
_SQL_RE = re.compile(
    r"\b(SELECT|INSERT|UPDATE|HAVING|GROUP\s+BY|ORDER\s+BY|FROM)\b",
    re.IGNORECASE,
)
_OPEN_TO_CLOSE = {"(": ")", "[": "]", "{": "}"}
_CLOSE_TO_OPEN = {")": "(", "]": "[", "}": "{"}


def _loc(line: int, col: int) -> str:
    return f"line {line}, column {col}"


def _advance(ch: str, line: int, col: int) -> tuple[int, int]:
    if ch == "\n":
        return line + 1, 1
    return line, col + 1


def _strip_optional_prefix(query: str) -> str:
    upper = query.upper()
    for prefix in ("EXPLAIN ", "PROFILE "):
        if upper.startswith(prefix):
            return query[len(prefix) :].lstrip()
    return query


def _validate_structure(cypher: str) -> tuple[str, str | None]:
    cleaned: list[str] = []
    stack: list[tuple[str, int, int]] = []

    state = "normal"
    quote_start: tuple[int, int] | None = None
    comment_start: tuple[int, int] | None = None

    i = 0
    line = 1
    col = 1
    length = len(cypher)

    while i < length:
        ch = cypher[i]
        nxt = cypher[i + 1] if i + 1 < length else ""

        if state == "line_comment":
            if ch == "\n":
                state = "normal"
                cleaned.append(" ")
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "normal"
                cleaned.append(" ")
                line, col = _advance(ch, line, col)
                line, col = _advance(nxt, line, col)
                i += 2
                continue
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if state == "single_quote":
            if ch == "\\" and nxt:
                line, col = _advance(ch, line, col)
                line, col = _advance(nxt, line, col)
                i += 2
                continue
            if ch == "'" and nxt == "'":
                line, col = _advance(ch, line, col)
                line, col = _advance(nxt, line, col)
                i += 2
                continue
            if ch == "'":
                state = "normal"
                cleaned.append(" ")
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if state == "double_quote":
            if ch == "\\" and nxt:
                line, col = _advance(ch, line, col)
                line, col = _advance(nxt, line, col)
                i += 2
                continue
            if ch == '"' and nxt == '"':
                line, col = _advance(ch, line, col)
                line, col = _advance(nxt, line, col)
                i += 2
                continue
            if ch == '"':
                state = "normal"
                cleaned.append(" ")
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if state == "backtick":
            if ch == "`" and nxt == "`":
                line, col = _advance(ch, line, col)
                line, col = _advance(nxt, line, col)
                i += 2
                continue
            if ch == "`":
                state = "normal"
                cleaned.append(" ")
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if ch == "/" and nxt == "/":
            state = "line_comment"
            cleaned.append(" ")
            line, col = _advance(ch, line, col)
            line, col = _advance(nxt, line, col)
            i += 2
            continue

        if ch == "/" and nxt == "*":
            state = "block_comment"
            comment_start = (line, col)
            cleaned.append(" ")
            line, col = _advance(ch, line, col)
            line, col = _advance(nxt, line, col)
            i += 2
            continue

        if ch == "'":
            state = "single_quote"
            quote_start = (line, col)
            cleaned.append(" ")
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if ch == '"':
            state = "double_quote"
            quote_start = (line, col)
            cleaned.append(" ")
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if ch == "`":
            state = "backtick"
            quote_start = (line, col)
            cleaned.append(" ")
            line, col = _advance(ch, line, col)
            i += 1
            continue

        if ch in _OPEN_TO_CLOSE:
            stack.append((ch, line, col))
        elif ch in _CLOSE_TO_OPEN:
            if not stack:
                return "", f"Unexpected '{ch}' at {_loc(line, col)}."
            opener, open_line, open_col = stack.pop()
            if opener != _CLOSE_TO_OPEN[ch]:
                expected = _OPEN_TO_CLOSE[opener]
                return "", (
                    f"Mismatched delimiter at {_loc(line, col)}: got '{ch}', "
                    f"expected '{expected}' to close '{opener}' from {_loc(open_line, open_col)}."
                )
        elif ch == ";":
            return "", "Semicolons are not allowed here. Send a single Cypher statement without ';'."

        cleaned.append(ch)
        line, col = _advance(ch, line, col)
        i += 1

    if state == "single_quote" and quote_start:
        return "", f"Unterminated single-quoted string opened at {_loc(*quote_start)}."
    if state == "double_quote" and quote_start:
        return "", f'Unterminated double-quoted string opened at {_loc(*quote_start)}.'
    if state == "backtick" and quote_start:
        return "", f"Unterminated backtick identifier opened at {_loc(*quote_start)}."
    if state == "block_comment" and comment_start:
        return "", f"Unterminated block comment opened at {_loc(*comment_start)}."
    if stack:
        opener, open_line, open_col = stack[-1]
        expected = _OPEN_TO_CLOSE[opener]
        return "", f"Unclosed '{opener}' from {_loc(open_line, open_col)}; expected '{expected}'."

    return "".join(cleaned), None


def parse_cypher_syntax(cypher: str) -> str | None:
    """Return an error message if the query is structurally invalid, else None."""
    query = (cypher or "").strip()
    if not query:
        return "Cypher query is empty."

    cleaned, error = _validate_structure(query)
    if error:
        return error

    normalized = re.sub(r"\s+", " ", _strip_optional_prefix(cleaned)).strip()
    if not normalized:
        return "Cypher query is empty."

    if _SQL_RE.search(normalized) and not _CLAUSE_RE.search(normalized):
        return "Query looks like SQL, but the database expects Cypher."

    if not _CLAUSE_RE.search(normalized):
        return "Missing Cypher clause. Start with MATCH, OPTIONAL MATCH, WITH, RETURN, UNWIND, or CALL."

    upper = normalized.upper()
    if "RETURN" not in upper and not upper.startswith("CALL "):
        return "Cypher query must include RETURN (or be a standalone CALL that yields results)."

    return None
