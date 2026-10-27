"""Block destructive or semantically unsafe Cypher before execution."""
from __future__ import annotations

import re

# ── Shared patterns and helpers (extracted to _common.py) ─────────────────────
from guardrails._common import (
    NODE_PATTERN_RE as _NODE_PATTERN_RE,
    REL_PATTERN_RE as _REL_PATTERN_RE,
    SCHEMA_LABEL_RE as _SCHEMA_LABEL_RE,
    SCHEMA_REL_RE as _SCHEMA_REL_RE,
    SCHEMA_PROP_RE as _SCHEMA_PROP_RE,
    QUERY_PROP_ACCESS_RE as _QUERY_PROP_ACCESS_RE,
    SYSTEM_TEMPORAL_ACCESSORS as _SYSTEM_TEMPORAL_ACCESSORS,
    normalize_text as _normalize_text,
    extract_schema_names as _extract_schema_names,
    extract_query_labels as _extract_query_labels,
    extract_query_relationships as _extract_query_relationships,
    extract_query_pattern_map_properties as _extract_query_pattern_map_properties,
    format_unknown_names as _format_unknown_names,
    schema_is_available as _schema_is_available,
)

_FUNCTIONAL_DATE_HINTS = (
    "recent",
    "recents",
    "recentes",
    "plus recent",
    "plus recents",
    "dernier",
    "derniers",
    "latest",
    "most recent",
    "date",
)
_TECHNICAL_TIMESTAMP_HINTS = (
    "created_at",
    "date de creation",
    "creation date",
    "timestamp de creation",
    "import",
    "importe",
    "imported",
    "cree dans la base",
    "created in the database",
)
_CHRONIC_DISEASE_HINTS = (
    "maladie chronique",
    "maladies chroniques",
    "chronic disease",
    "chronic diseases",
)
_CHRONIC_DISEASE_NEGATIVE_HINTS = (
    "sans maladie chronique",
    "sans maladies chroniques",
    "without chronic disease",
    "without chronic diseases",
    "pas de maladie chronique",
    "pas de maladies chroniques",
    "n'ont pas de maladie chronique",
    "n'a pas de maladie chronique",
)
_MALE_HINTS = (
    "homme",
    "hommes",
    "male",
    "males",
    "masculin",
    "masculins",
)
_FEMALE_HINTS = (
    "femme",
    "femmes",
    "female",
    "females",
    "feminin",
    "feminine",
    "feminins",
)
_SEX_PROPERTIES = ("sex", "sexe", "gender")
_CLAUSE_FOLLOWERS = r"(?:AND|OR|RETURN|WITH|ORDER\s+BY|LIMIT|SKIP|UNWIND|$)"
_BULLETIN_HINTS = (
    "bulletin",
    "bulletins",
    "bs",
    "feuille de soin",
    "feuilles de soin",
    "claim",
    "claims",
)
_OVER_CAP_HINTS = (
    "depasse leur plafond",
    "depassé leur plafond",
    "depassé le plafond",
    "depasse le plafond",
    "exceeded ceiling",
    "exceeded cap",
    "over cap",
)
_THIS_YEAR_HINTS = (
    "cette année",
    "cette annee",
    "this year",
    "année en cours",
    "annee en cours",
    "de l'année",
    "de l'annee",
    "of the year",
    "current year",
)


def _cypher_has_property_map_filter(cypher: str, prop: str) -> bool:
    pattern = rf"\{{[^{{}}]*\b{re.escape(prop)}\s*:"
    return bool(re.search(pattern, cypher or "", re.IGNORECASE | re.DOTALL))


def _cypher_has_property_comparison(cypher: str, prop: str) -> bool:
    patterns = (
        rf"\.\s*{re.escape(prop)}\b\s*(?:=|<>|!=|=~|IN\b|CONTAINS\b|STARTS\s+WITH\b|ENDS\s+WITH\b|IS\b)",
        rf"(?:toLower|toString)\s*\([^)]*\.{re.escape(prop)}[^)]*\)\s*(?:=|<>|!=|=~|IN\b|CONTAINS\b|STARTS\s+WITH\b|ENDS\s+WITH\b)",
    )
    return any(re.search(pattern, cypher or "", re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _cypher_has_boolean_filter(cypher: str, prop: str, expected: bool) -> bool:
    bool_literal = "true" if expected else "false"
    direct_patterns = (
        rf"\{{[^{{}}]*\b{re.escape(prop)}\s*:\s*{bool_literal}\b",
        rf"\.\s*{re.escape(prop)}\b\s*=\s*{bool_literal}\b",
        rf"\.\s*{re.escape(prop)}\b\s+IS\s+{bool_literal}\b",
    )
    if any(re.search(pattern, cypher or "", re.IGNORECASE | re.DOTALL) for pattern in direct_patterns):
        return True

    if expected:
        bare_pattern = rf"(?:WHERE|AND|OR)\s+\w+\.\s*{re.escape(prop)}\b(?=\s*{_CLAUSE_FOLLOWERS})"
    else:
        bare_pattern = rf"(?:WHERE|AND|OR)\s+NOT\s+\w+\.\s*{re.escape(prop)}\b(?=\s*{_CLAUSE_FOLLOWERS})"
    return bool(re.search(bare_pattern, cypher or "", re.IGNORECASE | re.DOTALL))


def _requested_chronic_disease(question: str) -> bool | None:
    q = _normalize_text(question)
    if any(hint in q for hint in _CHRONIC_DISEASE_NEGATIVE_HINTS):
        return False
    if any(hint in q for hint in _CHRONIC_DISEASE_HINTS):
        return True
    return None


def _schema_has_property(schema_context: str, prop: str) -> bool:
    return prop.lower() in _normalize_text(schema_context)


def _requested_sex(question: str) -> str | None:
    q = _normalize_text(question)
    if any(re.search(rf"\b{re.escape(hint)}\b", q) for hint in _MALE_HINTS):
        return "male"
    if any(re.search(rf"\b{re.escape(hint)}\b", q) for hint in _FEMALE_HINTS):
        return "female"
    return None


def _extract_bulletin_threshold(question: str) -> tuple[str, int] | None:
    q = _normalize_text(question)
    if not any(hint in q for hint in _BULLETIN_HINTS):
        return None

    # Ajout d'un lookahead négatif pour ignorer les valeurs suivies de %, pourcent, etc.
    patterns = (
        (r"(?:plus de|more than)\s+(\d+)(?!\s*(?:%|pour\s*cent|percent))", "gt"),
        (r"(?:au moins|at least|minimum de)\s+(\d+)(?!\s*(?:%|pour\s*cent|percent))", "gte"),
        (r"(?:moins de|less than)\s+(\d+)(?!\s*(?:%|pour\s*cent|percent))", "lt"),
        (r"(?:au plus|at most|maximum de|max de)\s+(\d+)(?!\s*(?:%|pour\s*cent|percent))", "lte"),
    )
    for pattern, operator in patterns:
        match = re.search(pattern, q, re.IGNORECASE)
        if match:
            return operator, int(match.group(1))
    return None


def _cypher_has_count_threshold(cypher: str, operator: str, threshold: int) -> bool:
    c = cypher or ""
    if not re.search(r"\bCOUNT\s*\(", c, re.IGNORECASE):
        return False

    accepted_patterns: list[str] = []
    if operator == "gt":
        accepted_patterns.append(rf">\s*{threshold}\b")
        accepted_patterns.append(rf">=\s*{threshold + 1}\b")
    elif operator == "gte":
        accepted_patterns.append(rf">=\s*{threshold}\b")
        if threshold > 0:
            accepted_patterns.append(rf">\s*{threshold - 1}\b")
    elif operator == "lt":
        accepted_patterns.append(rf"<\s*{threshold}\b")
        if threshold > 0:
            accepted_patterns.append(rf"<=\s*{threshold - 1}\b")
    elif operator == "lte":
        accepted_patterns.append(rf"<=\s*{threshold}\b")
        accepted_patterns.append(rf"<\s*{threshold + 1}\b")

    return any(re.search(pattern, c, re.IGNORECASE) for pattern in accepted_patterns)


def _requested_over_cap(question: str) -> bool:
    q = _normalize_text(question)
    return any(hint in q for hint in _OVER_CAP_HINTS)


def _requested_this_year(question: str) -> bool:
    q = _normalize_text(question)
    # Word-boundary match: a hint must appear as a whole phrase, not as a
    # substring of an unrelated word. This avoids false positives such as
    # "client" or a lone "année" triggering a mandatory year filter.
    return any(re.search(rf"(?:\b|\W){re.escape(hint)}(?:\b|\W)", q) for hint in _THIS_YEAR_HINTS)


def _cypher_has_over_cap_condition(cypher: str) -> bool:
    c = cypher or ""
    patterns = (
        r"\breste_plafond\b\s*(?:<=|<|=)\s*0\b",
        r"\bplafond\b\s*(?:-|/)\s*\b(?:reste|consomme|consommation)\b",  # loose fallback
    )
    return any(re.search(pattern, c, re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _cypher_has_dynamic_this_year_filter(cypher: str) -> bool:
    c = (cypher or "").lower()
    # Enforce dynamic current-year anchor, not hardcoded literal years.
    return "date().year" in c or "datetime().year" in c


def explicit_constraint_semantic_check(
    *,
    question: str,
    cypher: str,
    schema_context: str,
) -> str | None:
    """
    Reject Cypher that drops explicit user constraints such as chronic disease,
    sex/gender filters, or bulletin count thresholds.
    """
    missing_constraints: list[str] = []
    schema = _normalize_text(schema_context)

    chronic_disease = _requested_chronic_disease(question)
    if chronic_disease is not None:
        # Support either `malade_chron` or `is_chronique` (chronic_disease has been removed)
        has_filter = (
            _cypher_has_boolean_filter(cypher, "malade_chron", chronic_disease)
            or _cypher_has_boolean_filter(cypher, "is_chronique", chronic_disease)
        )
        if not has_filter:
            expected = "true" if chronic_disease else "false"
            missing_constraints.append(f"`malade_chron = {expected}`")

    requested_sex = _requested_sex(question)
    if requested_sex is not None:
        candidate_props = [
            prop
            for prop in _SEX_PROPERTIES
            if _schema_has_property(schema, prop)
        ] or list(_SEX_PROPERTIES)
        if not any(
            _cypher_has_property_map_filter(cypher, prop)
            or _cypher_has_property_comparison(cypher, prop)
            for prop in candidate_props
        ):
            label = "male" if requested_sex == "male" else "female"
            missing_constraints.append(f"a sex/gender filter for `{label}`")

    bulletin_threshold = _extract_bulletin_threshold(question)
    if bulletin_threshold is not None:
        operator, threshold = bulletin_threshold
        if not _cypher_has_count_threshold(cypher, operator, threshold):
            symbols = {
                "gt": ">",
                "gte": ">=",
                "lt": "<",
                "lte": "<=",
            }
            missing_constraints.append(
                f"a bulletin count threshold `{symbols[operator]} {threshold}`"
            )

    if _requested_over_cap(question):
        if not _cypher_has_over_cap_condition(cypher):
            missing_constraints.append("an explicit over-cap condition (e.g. `reste_plafond <= 0`)")

    if _requested_this_year(question):
        if not _cypher_has_dynamic_this_year_filter(cypher):
            missing_constraints.append("a dynamic current-year filter (e.g. `date().year` anchor)")

    if not missing_constraints:
        return None

    return (
        "The query is missing explicit user constraints from the question: "
        + ", ".join(missing_constraints)
        + ". Regenerate the Cypher and verify that every explicit filter or threshold "
        "requested by the user is represented before finalizing."
    )


def schema_name_semantic_check(
    *,
    cypher: str,
    schema_context: str,
) -> str | None:
    """
    Reject Cypher that invents labels, relationship types, or property names
    that are not present in the current schema context.
    """
    if not _schema_is_available(schema_context):
        return None

    allowed_labels, allowed_relationships, allowed_properties = _extract_schema_names(
        schema_context
    )
    if not allowed_labels and not allowed_relationships and not allowed_properties:
        return None

    unknown_labels = _extract_query_labels(cypher) - allowed_labels
    unknown_relationships = _extract_query_relationships(cypher) - allowed_relationships
    referenced_properties = _extract_query_pattern_map_properties(cypher) | set(
        _QUERY_PROP_ACCESS_RE.findall(cypher or "")
    )
    # Ignore temporal accessor names used on built-ins like date().year,
    # datetime().month, etc. These are not domain schema properties.
    referenced_properties = {
        prop
        for prop in referenced_properties
        if prop.lower() not in _SYSTEM_TEMPORAL_ACCESSORS
    }
    unknown_properties = referenced_properties - allowed_properties if allowed_properties else set()

    problems: list[str] = []
    if unknown_labels:
        problems.append(f"unknown labels: {_format_unknown_names(unknown_labels)}")
    if unknown_relationships:
        problems.append(
            "unknown relationship types: "
            + _format_unknown_names(unknown_relationships)
        )
    if unknown_properties:
        problems.append(
            "unknown properties: " + _format_unknown_names(unknown_properties)
        )

    if not problems:
        return None

    return (
        "The query uses names that do not appear in the available schema context: "
        + "; ".join(problems)
        + ". Regenerate the Cypher using only labels, relationship types, and properties "
        "that appear literally in AVAILABLE SCHEMA."
    )
