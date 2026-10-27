"""
cypher_validator.py — v2 (fixes C2, C3, C4)

FIX C2 — Unification des sources de topologie
──────────────────────────────────────────────
AVANT : get_topology_cached_or_fetch() (topology.py → apoc.meta.schema)
        puis get_dynamic_topology() (query_guard_patch.py → db.schema.visualization)
        → 2 sources différentes, 2 caches indépendants, possible divergence.

APRÈS : une seule variable `domain_topology` chargée une fois en ligne ~80,
        passée directement à graph_path_semantic_check().
        get_dynamic_topology() supprimé des imports.

FIX C3 — Élimination du double appel réseau Neo4j
──────────────────────────────────────────────────
AVANT : cold start = 2 appels réseau séquentiels (~250ms).
APRÈS : 1 seul appel réseau via get_topology_cached_or_fetch(),
        résultat réutilisé partout dans la même requête.

FIX C4 — Skip EXPLAIN sur retries non-syntaxiques
──────────────────────────────────────────────────
AVANT : EXPLAIN Neo4j lancé à chaque validation, même sur retry
        dont la cause précédente était un problème de schéma/sémantique.
APRÈS : EXPLAIN sauté si le retry précédent avait échoué pour une
        raison autre que "explain" ou "ast_parse" (erreur de schéma,
        de chemin, ou de contrainte → pas besoin de revalider la syntaxe
        Neo4j, les gardes statiques suffisent).
        EXPLAIN est toujours forcé sur retry_count == 0 (premier passage)
        et sur reason == "explain" (dernier échec était syntaxique Neo4j).
"""

import logging
import re
import time
from agent.state import AgentState
from agent.trace_util import step
from config.settings import get_settings
from graph.validators.cypher_ast import parse_cypher_syntax
from graph.validators.dry_runner import explain_cypher

logger = logging.getLogger(__name__)

# ── Existing guardrails ───────────────────────────────────────────────────────
from guardrails.query_guard import (
    explicit_constraint_semantic_check,
)

# ── Patched guardrails — FIX C2/C3 : get_dynamic_topology supprimé ───────────
from guardrails.query_guard_patch import (
    graph_path_semantic_check,
    schema_name_semantic_check_v2,
)

# ── Source unique de topologie (FIX C2/C3) ────────────────────────────────────
from graph.schema.topology import get_topology_cached_or_fetch
from graph.schema.property_registry import format_property_registry

# ── Raisons d'échec qui ne nécessitent PAS un re-EXPLAIN (FIX C4) ─────────────
_SKIP_EXPLAIN_REASONS = frozenset({
    "semantic_guard",
    "schema_name_guard",
    "graph_path_guard",
})


def _should_skip_explain(retry_count: int, last_reason: str | None) -> bool:
    """
    FIX C4 — Retourne True si l'EXPLAIN Neo4j peut être sauté sur ce retry.

    Logique :
      - retry_count == 0 : premier passage, EXPLAIN obligatoire.
      - last_reason in _SKIP_EXPLAIN_REASONS : l'échec précédent était
        sémantique/schéma, pas syntaxique Neo4j → EXPLAIN inutile.
      - Sinon (reason == "explain", "ast_parse", ou inconnu) : EXPLAIN requis.
    """
    if retry_count == 0:
        return False
    if last_reason in _SKIP_EXPLAIN_REASONS:
        return True
    return False


def run(state: AgentState) -> dict:
    cypher = state.get("cypher_draft", "")
    retry_count = state.get("retry_count", 0)
    # FIX C4 : récupère la raison du dernier échec pour décider du skip EXPLAIN
    last_validation_reason = state.get("last_validation_reason")

    s = get_settings()
    graph_access_configured = getattr(
        s,
        "graph_access_configured",
        lambda: bool(s.neo4j_auth_user()),
    )

    if not graph_access_configured():
        return _invalid(
            retry_count,
            reason="config",
            error="Missing graph access config. Set MCP_URL or NEO4J_USER/NEO4J_USERNAME.",
        )

    # ── 0. Markdown stripper ──────────────────────────────────────────────────
    t0 = time.perf_counter()
    if "```" in cypher:
        match = re.search(r"```(?:cypher|sql)?\s*(.*?)\s*```", cypher, re.IGNORECASE | re.DOTALL)
        cypher = match.group(1).strip() if match else cypher.replace("```cypher", "").replace("```", "").strip()
        state["cypher_draft"] = cypher
    t_markdown = time.perf_counter() - t0

    # ── 1. Local AST parse ────────────────────────────────────────────────────
    t0 = time.perf_counter()
    if err := parse_cypher_syntax(cypher):
        return _invalid(retry_count, reason="ast_parse", error=err)
    t_ast = time.perf_counter() - t0

    # ── 2. Chargement de la topologie — source unique (FIX C2/C3) ────────────
    # get_topology_cached_or_fetch() utilise un cache TTL thread-safe.
    # Si cypher_generator a déjà peuplé le cache, aucun appel réseau ici.
    t0 = time.perf_counter()
    base_schema = state.get("schema_context", "") or ""
    domain_topology, topology_triple_count, topology_source = get_topology_cached_or_fetch()
    registry = format_property_registry()
    full_schema = f"{registry}\n\n{base_schema}\n{domain_topology}"
    t_topology = time.perf_counter() - t0

    # ── 3. Explicit constraint heuristics ─────────────────────────────────────
    t0 = time.perf_counter()
    if err := explicit_constraint_semantic_check(
        question=state.get("question", ""),
        cypher=cypher,
        schema_context=full_schema,
    ):
        return _invalid(retry_count, reason="semantic_guard", error=err)
    t_semantic = time.perf_counter() - t0

    t0 = time.perf_counter()
    if err := schema_name_semantic_check_v2(
        cypher=cypher,
        schema_context=full_schema,
    ):
        return _invalid(retry_count, reason="schema_name_guard", error=err)
    t_schema_name = time.perf_counter() - t0

    # ── 4. Graph path topology check — domain_topology réutilisé (FIX C2/C3) ─
    # On passe directement domain_topology déjà chargé ci-dessus.
    # Plus d'appel à get_dynamic_topology() (source différente, cache séparé).
    t0 = time.perf_counter()
    if err := graph_path_semantic_check(
        cypher=cypher,
        domain_topology=domain_topology,   # ← variable locale, pas get_dynamic_topology()
    ):
        return _invalid(retry_count, reason="graph_path_guard", error=err)
    t_path = time.perf_counter() - t0

    # ── 5. Neo4j EXPLAIN dry-run — FIX C4 : skip si retry sémantique ─────────
    t0 = time.perf_counter()
    skip_explain = _should_skip_explain(retry_count, last_validation_reason)
    if not skip_explain:
        if err := explain_cypher(cypher):
            return _invalid(retry_count, reason="explain", error=err)
    t_explain = time.perf_counter() - t0

    logger.info(
        "validator_timings retry=%d markdown=%.1fms ast=%.1fms topology=%.1fms "
        "semantic=%.1fms schema_name=%.1fms path=%.1fms explain=%.1fms skip_explain=%s",
        retry_count,
        t_markdown * 1000, t_ast * 1000, t_topology * 1000,
        t_semantic * 1000, t_schema_name * 1000, t_path * 1000, t_explain * 1000,
        skip_explain,
    )

    # ── All checks passed ──────────────────────────────────────────────────────
    return {
        "validation_error": None,
        "retry_count": retry_count,
        "last_validation_reason": None,   # reset après succès
        "trace_steps": [
            step(
                "cypher_validator",
                "valid",
                checks=[
                    "ast_parse",
                    "explicit_constraint_guard",
                    "schema_name_guard",
                    "graph_path_guard",
                    "neo4j_explain" if not skip_explain else "neo4j_explain_skipped",
                ],
                neo4j_explain_ok=not skip_explain,
                explain_skipped=skip_explain,
                topology_source=topology_source,
                topology_triple_count=topology_triple_count,
            )
        ],
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _invalid(retry_count: int, *, reason: str, error: str) -> dict:
    return {
        "validation_error": error,
        "retry_count": retry_count + 1,
        "last_validation_reason": reason,  # FIX C4 : stocké pour le prochain retry
        "trace_steps": [
            step(
                "cypher_validator",
                "invalid",
                reason=reason,
                error=error,
            )
        ],
    }
