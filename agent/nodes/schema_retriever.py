import re
import unicodedata
from typing import Any

from agent.state import AgentState
from agent.trace_util import step
from graph.schema.property_catalog import format_enriched_schema
from graph.schema.schema_manager import get_full_schema_cached_or_fetch
from graph.schema.value_catalog import append_enum_hints_to_context

_CAMEL_CASE_BOUNDARY = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
)
_ALNUM_TOKEN = re.compile(r"[a-z0-9]+")
_SHORT_DOMAIN_TOKENS = {"bs", "dci", "icd", "tpa"}
_TOKEN_ALIASES = {
    "assureur": {"insurer"},
    "insurer": {"assureur"},
    "beneficiaire": {"beneficiary"},
    "beneficiary": {"beneficiaire"},
    "contrat": {"contract"},
    "contract": {"contrat"},
    "offre": {"offer"},
    "offer": {"offre"},
    "chapitre": {"chapter"},
    "chapter": {"chapitre"},
    "consommation": {"consumption"},
    "consumption": {"consommation"},
    "plafond": {"ceiling"},
    "ceiling": {"plafond"},
    "limite": {"limit"},
    "limit": {"limite"},
    "lettre": {"letter"},
    "letter": {"lettre"},
    "medecin": {"physician", "doctor"},
    "physician": {"medecin", "doctor"},
    "doctor": {"medecin", "physician"},
    "specialite": {"specialty"},
    "specialty": {"specialite"},
    "soin": {"care"},
    "care": {"soin"},
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_token_text(text: str) -> str:
    text = _strip_accents(text or "")
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = re.sub(r"[_:/\\.\-]+", " ", text)
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)
    return text.lower()


def _tokenize(text: str) -> set[str]:
    raw_tokens = _ALNUM_TOKEN.findall(_normalize_token_text(text))
    tokens = {
        token
        for token in raw_tokens
        if len(token) > 2 or token in _SHORT_DOMAIN_TOKENS
    }
    expanded = set(tokens)
    for token in list(tokens):
        expanded.update(_TOKEN_ALIASES.get(token, set()))
    return expanded


def _match_score(name: str, question_tokens: set[str]) -> int:
    name_tokens = _tokenize(name.replace(":", " "))
    overlap = question_tokens & name_tokens
    return len(overlap)


def _relationship_has_data(rel_info: dict[str, Any]) -> bool:
    count = rel_info.get("count")
    if isinstance(count, (int, float)):
        return count > 0
    return True


def _format_schema(meta_map: dict, question: str, question_tokens: set[str] | None = None) -> str:
    if question_tokens is None:
        question_tokens = _tokenize(question) if question else set()
    selected_nodes: list[str] = []

    for label, details in meta_map.items():
        if not isinstance(details, dict):
            continue
        if details.get("type") != "node":
            continue
        score = _match_score(label, question_tokens)
        if score > 0 or not question_tokens:
            selected_nodes.append(label)

    if not selected_nodes:
        selected_nodes = [
            label
            for label, details in meta_map.items()
            if isinstance(details, dict) and details.get("type") == "node"
        ][:15]

    return format_enriched_schema(meta_map, selected_nodes, question_tokens=question_tokens, show_properties=False)



MISSING_CREDENTIALS_SCHEMA_MESSAGE = (
    "Schema unavailable: missing Neo4j credentials "
    "(set NEO4J_USER or NEO4J_USERNAME, plus NEO4J_PASSWORD)."
)

INTROSPECTION_UNAVAILABLE_MESSAGE = (
    "Schema unavailable: dynamic Neo4j schema discovery failed on the connected instance."
)


def resolve_schema_for_question(question: str) -> dict[str, Any]:
    """
    Compute the same schema_context string as the agent (no LangGraph / trace).
    """
    from config.settings import get_settings

    q = (question or "").strip()
    s = get_settings()
    graph_access_configured = getattr(
        s,
        "graph_access_configured",
        lambda: bool(s.neo4j_auth_user()),
    )
    if not graph_access_configured():
        return {
            "ok": False,
            "error": "missing_neo4j_credentials",
            "schema_mode": "config_error",
            "schema_context": MISSING_CREDENTIALS_SCHEMA_MESSAGE,
            "focus_labels": None,
        }

    schema_mode = "token_filter"
    try:
        meta_map = get_full_schema_cached_or_fetch()
        question_tokens = _tokenize(q) if q else set()
        schema_context = _format_schema(meta_map, q, question_tokens=question_tokens)
        schema_context = append_enum_hints_to_context(schema_context)
        return {
            "ok": True,
            "schema_mode": schema_mode,
            "schema_context": schema_context,
            "focus_labels": None,
            "focus_label_count": 0,
            "schema_chars": len(schema_context),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": "neo4j_introspection_failed",
            "detail": str(exc),
            "schema_mode": "neo4j_introspection_unavailable",
            "schema_context": INTROSPECTION_UNAVAILABLE_MESSAGE,
            "focus_labels": None,
            "schema_chars": len(INTROSPECTION_UNAVAILABLE_MESSAGE),
        }


def run(state: AgentState) -> dict:
    question = state.get("question", "")
    resolved = resolve_schema_for_question(question)
    schema_context = resolved["schema_context"]
    schema_mode = resolved["schema_mode"]
    preview = schema_context[:600]

    if resolved.get("ok") is False and resolved.get("error") == "missing_neo4j_credentials":
        return {
            "schema_context": schema_context,
            "trace_steps": [
                step(
                    "schema_retriever",
                    "schema_context_ready",
                    schema_mode=schema_mode,
                    detail="Missing NEO4J_USER / NEO4J_USERNAME",
                    schema_preview=preview,
                )
            ],
        }

    return {
        "schema_context": schema_context,
        "trace_steps": [
            step(
                "schema_retriever",
                "schema_context_ready",
                schema_mode=schema_mode,
                schema_chars=len(schema_context),
                focus_labels=resolved.get("focus_labels"),
                schema_preview=preview,
            )
        ],
    }
