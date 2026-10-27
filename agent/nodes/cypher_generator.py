"""
cypher_generator.py — v2 (fixes C1)

FIX C1 — Alignement Generator / Validator sur le même full_schema
──────────────────────────────────────────────────────────────────
AVANT : le generator passait state["schema_context"] brut au LLM.
        Le validator construisait full_schema = base + domain_topology.
        → Le LLM voyait un schéma tronqué (DCI, Bordereau, InsuranceContract...
          absents) → générait des chemins invalides → boucle retry inutile.

APRÈS : on enrichit le schema_context avec la même domain_topology
        que le validator AVANT l'appel LLM. Generator et validator
        voient désormais exactement le même schéma complet.
        Le cache TTL de get_topology_cached_or_fetch() garantit
        qu'aucun appel réseau supplémentaire n'est fait (même objet
        retourné au validator juste après).
"""
from __future__ import annotations

import re
import unicodedata

from agent.state import AgentState
from agent.trace_util import step
from llm.prompts.cypher_system import build_cypher_system_prompt
from llm.router import get_provider

# ── FIX C1 : import unique du cache de topologie ──────────────────────────────
from graph.schema.topology import get_topology_cached_or_fetch
from graph.schema.property_registry import format_property_registry
from graph.schema.value_catalog import append_enum_hints_to_context


_MEDICATION_QUERY_TOKENS = {
    "medicament",
    "medicaments",
    "medication",
    "medications",
    "drug",
    "drugs",
    "produit",
    "produits",
    "product",
    "products",
}
_USAGE_QUERY_TOKENS = {
    "utilise",
    "utilisee",
    "utilises",
    "utilisees",
    "frequent",
    "frequents",
    "frequence",
    "usage",
    "used",
    "most",
    "top",
    "souvent",
}
_DISEASE_QUERY_TOKENS = {
    "maladie",
    "maladies",
    "disease",
    "diseases",
    "type",
}
_MEDICATION_QUERY_REQUIRED_SCHEMA_TOKENS = {
    "Product",
    "DCI",
    "BulletinSoinPrestationDetail",
    "BulletinSoinPrestation",
    "HAS_DCI",
    "USES_PRODUCT",
    "CREATED_UNDER",
}
_DISEASE_TYPE_PATTERNS = [
    re.compile(r"\bmaladies?\s+(?:de\s+)?type\s+([a-z0-9]+(?:\s+[a-z0-9]+){0,2})\b"),
    re.compile(r"\bdiseases?\s+type\s+([a-z0-9]+(?:\s+[a-z0-9]+){0,2})\b"),
]
_CURRENT_QUESTION_MARKER = "Current user question:"
_CONTEXT_ERROR_MARKERS = (
    "maximum context length",
    "requested",
    "reduce the length of the messages",
    "context length exceeded",
    "too many tokens",
)


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    without_accents = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    )
    compact = re.sub(r"[^a-zA-Z0-9]+", " ", without_accents)
    return " ".join(compact.lower().split())


def _extract_disease_type_term(question: str) -> str | None:
    normalized = _normalize_text(question)
    for pattern in _DISEASE_TYPE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return match.group(1).strip()
    return None


def _extract_current_question(question: str) -> str:
    text = (question or "").strip()
    if not text:
        return ""
    if _CURRENT_QUESTION_MARKER not in text:
        return text
    _, _, tail = text.partition(_CURRENT_QUESTION_MARKER)
    return tail.strip() or text


def _is_context_length_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "context" in message
        and any(marker in message for marker in _CONTEXT_ERROR_MARKERS)
    )


def _build_full_schema(base_schema: str) -> str:
    """
    Construit le schéma envoyé au LLM.

    Référence des NŒUDS/PROPRIÉTÉS = format_property_registry() (curated,
    property_registry.py) UNIQUEMENT. La topologie (chemins + directions)
    est injectée dynamiquement depuis le cache TTL (aucun appel réseau
    supplémentaire si le validator a déjà peuplé le cache).

    Le base_schema dynamique (introspection Neo4j, show_properties=False)
    n'est plus envoyé au LLM : il ne sert qu'aux garde-fous du validator.

    Le bloc KNOWN VALUES (value_catalog) est ré-appliqué ici car le
    base_schema — qui le portait — n'est plus inclus : c'est la source #1
    de la détection dynamique des énumérations (point 3 du prompt).
    """
    domain_topology, _, _ = get_topology_cached_or_fetch()
    registry = format_property_registry()
    return append_enum_hints_to_context(f"{registry}\n\n{domain_topology}")


# ── Point 4 : détection de la catégorie de few-shots ────────────────────────
_FEW_SHOT_CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "prescription": {
        "produit", "produits", "medicament", "medicaments", "medication",
        "prescrit", "prescrite", "prescription", "drug", "drugs", "product",
        "products", "pharmacie", "pharma",
    },
    "consommation": {
        "plafond", "plafonds", "ceiling", "consommation", "consomme",
        "consommee", "consumption", "depasse", "depasse", "depassement",
        "reste", "reste_plafond", "epuise", "epuisement",
    },
    "consultation": {
        "medecin", "medecins", "physician", "specialite", "specialites",
        "specialty", "consultation", "consultations", "cardio",
    },
    "diagnostic": {
        "maladie", "maladies", "disease", "diseases", "chronique",
        "chroniques", "chronic", "pathologie", "pathologies", "diabete",
        "diabetes", "dci", "hypertension", "diagnostic", "diagnostics",
    },
}


def _detect_few_shot_category(question: str) -> str | None:
    """Lightweight keyword scoring — no LLM call."""
    normalized = _normalize_text(question or "")
    words = set(normalized.split())
    best_category: str | None = None
    best_score = 0
    for category, keywords in _FEW_SHOT_CATEGORY_KEYWORDS.items():
        score = len(words & keywords)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category if best_score > 0 else None


def _generate_with_prompt_fallbacks(
    *,
    question: str,
    schema_context: str,
    validation_error: str | None,
    cypher_draft: str | None,
    few_shot_category: str | None = None,
) -> tuple[str, str, dict[str, str]]:
    provider = get_provider()
    compact_question = _extract_current_question(question)
    attempts = [
        (
            "llm",
            build_cypher_system_prompt(
                schema=schema_context,
                validation_error=validation_error,
                few_shot_category=few_shot_category,
            ),
            question,
        ),
        (
            "llm_compact_prompt",
            build_cypher_system_prompt(
                schema=schema_context,
                validation_error=validation_error,
                compact=True,
                max_schema_chars=2500,
                include_examples=True,
            ),
            compact_question,
        ),
        (
            "llm_minimal_prompt",
            build_cypher_system_prompt(
                schema=schema_context,
                validation_error=validation_error,
                compact=True,
                max_schema_chars=1400,
                include_examples=False,
            ),
            compact_question,
        ),
    ]

    last_exc: Exception | None = None
    provider_meta = {
        "provider": str(getattr(provider, "provider_label", provider.__class__.__name__)),
        "model": str(getattr(provider, "model", "")),
    }
    for generation_mode, system_prompt, prompt_question in attempts:
        try:
            cypher = provider.generate_cypher(
                system_prompt=system_prompt,
                question=prompt_question,
                cypher_draft=cypher_draft,
                validation_error=validation_error,
            )
            provider_meta["system_prompt_chars"] = str(len(system_prompt))
            provider_meta["question_chars"] = str(len(prompt_question or ""))
            return cypher, generation_mode, provider_meta
        except Exception as exc:
            last_exc = exc
            if not _is_context_length_error(exc):
                raise

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("LLM generation failed without a captured exception.")


def _maybe_build_medication_usage_cypher(
    *,
    question: str,
    schema_context: str,
) -> str | None:
    normalized = _normalize_text(question)
    tokens = set(normalized.split())
    if not (
        tokens & _MEDICATION_QUERY_TOKENS
        and tokens & _USAGE_QUERY_TOKENS
        and tokens & _DISEASE_QUERY_TOKENS
    ):
        return None

    disease_term = _extract_disease_type_term(question)
    if not disease_term:
        return None

    if not all(token in schema_context for token in _MEDICATION_QUERY_REQUIRED_SCHEMA_TOKENS):
        return None

    disease_literal = disease_term.replace("'", "\\'")
    return (
        "MATCH (d:DCI)<-[:HAS_DCI]-(p:Product)"
        "<-[:USES_PRODUCT]-(det:BulletinSoinPrestationDetail)"
        "-[:CREATED_UNDER]->(bsp:BulletinSoinPrestation)\n"
        f"WHERE toLower(coalesce(d.drug_description, '')) CONTAINS '{disease_literal}'\n"
        f"   OR toLower(coalesce(d.drug_description_french_dci, '')) CONTAINS '{disease_literal}'\n"
        f"   OR toLower(coalesce(d.indications, '')) CONTAINS '{disease_literal}'\n"
        "RETURN p.name AS product_name, COUNT(det) AS usage_count\n"
        "ORDER BY usage_count DESC, product_name ASC\n"
        "LIMIT 20"
    )


def run(state: AgentState) -> dict:
    base_schema = state.get("schema_context", "") or ""

    # ── FIX C1 : enrichir le schéma exactement comme le fait le validator ────
    # get_topology_cached_or_fetch() utilise un cache TTL — aucun appel réseau
    # supplémentaire si le validator a déjà peuplé le cache dans la même requête.
    full_schema = _build_full_schema(base_schema)

    cypher = _maybe_build_medication_usage_cypher(
        question=state["question"],
        # Le gate de l'heuristique vérifie DCI/HAS_DCI, tokens qui n'existent
        # QUE dans le base_schema dynamique (pas dans registry + topologie).
        schema_context=base_schema,
    )
    generation_mode = "heuristic_template"
    provider_meta: dict[str, str] = {}
    if cypher is None:
        cypher, generation_mode, provider_meta = _generate_with_prompt_fallbacks(
            question=state["question"],
            schema_context=full_schema,      # full_schema au lieu de state["schema_context"]
            validation_error=state.get("validation_error"),
            cypher_draft=state.get("cypher_draft"),
            few_shot_category=_detect_few_shot_category(state["question"]),
        )

    if cypher.startswith("```"):
        cypher = cypher.split("```")[1]
        if cypher.startswith("cypher"):
            cypher = cypher[6:]
        cypher = cypher.strip()

    return {
        "cypher_draft": cypher,
        "validation_error": None,
        "trace_steps": [
            step(
                "cypher_generator",
                "cypher_draft",
                retry_attempt=int(state.get("retry_count") or 0),
                generation_mode=generation_mode,
                provider=provider_meta.get("provider"),
                model=provider_meta.get("model"),
                system_prompt_chars=provider_meta.get("system_prompt_chars"),
                question_chars=provider_meta.get("question_chars"),
                cypher=cypher,
            )
        ],
    }
