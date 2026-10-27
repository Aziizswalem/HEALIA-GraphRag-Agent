"""System prompt for Cypher generation — v4.3.

CHANGES vs v4.2:
1. Point 5 — Topology is no longer referenced from this module: the dead
   `DOMAIN_TOPOLOGY` import was removed. The schema block is injected
   dynamically by cypher_generator (registry + topology at call time).
2. Point 3 — Exact-match properties are now detected DYNAMICALLY from the
   schema's "KNOWN VALUES SAMPLED FROM DATABASE" block and from the
   property-registry descriptions (quoted literals). The hardcoded
   _EXACT_MATCH_PROPERTIES set is gone.
3. Point 2 — SOFT_NOTES trimmed: business vocab mappings that duplicated
   HARD_RULES (e.g. generic CONTAINS advice) were removed. Only unique
   business mappings remain (plafond chapitre, DCI, gender, etc.).
4. Point 6 — Rule 7 extended with an explicit WITH-binding example for
   year-age filters (date().year - prop.year), avoiding invalid
   duration.between() usage on DATE values.
5. Point 4 — build_cypher_system_prompt() accepts few_shot_category to
   inject only the relevant few-shot block (fewer tokens, more focus).
"""
from __future__ import annotations

import re

from llm.prompts.few_shots import (
    consultation_queries,
    consommation_queries,
    diagnostic_queries,
    prescription_queries,
)
from llm.prompts.retry_injection import format_validation_retry_block

FEW_SHOT_MODULES = {
    "prescription": prescription_queries,
    "consommation": consommation_queries,
    "consultation": consultation_queries,
    "diagnostic": diagnostic_queries,
}

FEW_SHOTS = "\n\n".join([
    prescription_queries.FEW_SHOTS.strip(),
    consommation_queries.FEW_SHOTS.strip(),
    consultation_queries.FEW_SHOTS.strip(),
    diagnostic_queries.FEW_SHOTS.strip(),
])

_COMPACT_FEW_SHOTS = """
### Q: Quels assureurs sont actifs dans le système ?
MATCH (a:Assureur)
RETURN a.id AS assureur_id, a.name AS nom
ORDER BY a.name

### Q: Combien de bulletins de soin par assuré ?
MATCH (bs:BulletinSoin)-[:CREATED_FOR]->(a:Assure)
RETURN a.id AS assure_id, a.first_name AS prenom, a.last_name AS nom,
       count(bs) AS nb_bulletins
ORDER BY nb_bulletins DESC
LIMIT 50

### Q: Lister tous les details prestations de l'adherent 1426
# KEY: "adherent <number>" means Assure.id (number not string).
# KEY: correct path is BulletinSoin <- BELONGS_TO_BS - Prestation <- CREATED_UNDER - Detail.
MATCH (a:Assure {id: 1426})<-[:CREATED_FOR]-(bs:BulletinSoin)
MATCH (p:BulletinSoinPrestation)-[:BELONGS_TO_BS]->(bs)
MATCH (det:BulletinSoinPrestationDetail)-[:CREATED_UNDER]->(p)
OPTIONAL MATCH (det)-[:USES_PRODUCT]->(prod:Product)
OPTIONAL MATCH (det)-[:COVERED_BY_CHAPTER]->(chap:InsuranceOfferChapitre)
RETURN a.id AS adherent,
       bs.num_bs AS num_bs,
       toString(p.date_prestation) AS date_prestation,
       p.discipline AS prestation_discipline,
       p.montant_depense AS prestation_montant_depense,
       p.montant_pec AS prestation_montant_pec,
       det.id AS detail_id,
       det.discipline AS detail_discipline,
       det.montant_depense AS detail_montant_depense,
       det.montant_pec AS detail_montant_pec,
       det.qty AS quantite,
       prod.name AS produit,
       chap.name AS chapitre
ORDER BY p.date_prestation DESC, det.id

### Q: Assurés ayant dépassé leur plafond cette année, par assureur
# PATH: BulletinSoin -[:AFFECTS]-> InsuranceContractConsommation -[:CONCERNS_ASSURE]-> Assure
# KEY: reste_plafond is on InsuranceContractConsommation, NOT on BulletinSoin
MATCH (bs:BulletinSoin)-[:AFFECTS]->(icc:InsuranceContractConsommation)-[:CONCERNS_ASSURE]->(a:Assure),
      (bs)-[:COVERED_BY]->(assureur:Assureur)
WHERE bs.validation_date >= date({year: date().year, month: 1, day: 1})
  AND icc.reste_plafond <= 0
RETURN assureur.name AS assureur,
       count(DISTINCT a.id) AS nb_assures_depasses
ORDER BY nb_assures_depasses DESC

### Q: Quels produits sont les plus prescrits ?
MATCH (d:BulletinSoinPrestationDetail)-[:USES_PRODUCT]->(p:Product)
RETURN p.name AS produit, count(d) AS nb_prescriptions
ORDER BY nb_prescriptions DESC
LIMIT 20

### Q: Assurés avec plus de consultations que moyenne + 2 écarts-types
# MEMORY-SAFE: compute stats first, then collect+UNWIND — never collect full dataset raw
MATCH (bs:BulletinSoin)-[:CREATED_FOR]->(a:Assure)
WITH a, count(bs) AS nb_bs
WITH avg(nb_bs) AS moyenne,
     stDev(nb_bs) AS ecart_type,
     collect({assure: a, nb: nb_bs}) AS data
UNWIND data AS row
WITH row.assure AS a, row.nb AS nb_bs, moyenne, ecart_type
WHERE nb_bs > moyenne + 2 * ecart_type
RETURN a.id AS assure_id, a.first_name AS prenom, a.last_name AS nom,
       nb_bs, round(moyenne, 1) AS moyenne, round(ecart_type, 1) AS ecart_type
ORDER BY nb_bs DESC
""".strip()

_ENUM_HINTS_MARKER = "\nKNOWN VALUES SAMPLED FROM DATABASE"
_ENUM_HINTS_KEY_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_]*\.[A-Za-z][A-Za-z0-9_]*)\s*:")
# Registry lines: `  <pname><pad><TYPE> — description : 'enum1', 'enum2'`
# The colon is NOT contiguous with the property name (padding + type), so
# capture: 2-space indent, prop name, padding, TYPE, then a quoted lowercase
# literal after a colon (e.g. "État : 'refunded'"). French apostrophes in
# descriptions ("l'assuré") never precede a colon, so they can't false-match.
_REGISTRY_PROP_RE = re.compile(
    r"^\s{2}([a-z][a-z0-9_]*)\s{2,}[A-Z][A-Z0-9_]*[^\n]*?:\s*'([a-z][a-z0-9_]+)'"
)
# Generic free-text keys that must NEVER become exact-match — they are the
# CONTAINS/fuzzy-matching backbone (names, addresses, identifiers).
_REGISTRY_FREE_TEXT_KEYS = {
    "name",
    "first_name",
    "last_name",
    "complete_name",
    "street",
    "street2",
    "id",
    "police",
    "list_msg",
    "conditions",
}

_EXACT_MATCH_PROPERTIES: set[str] = set()


def _extract_exact_match_properties(schema: str) -> set[str]:
    """Dynamically discover properties that should use EXACT value match.

    Sources:
      1. The "KNOWN VALUES SAMPLED FROM DATABASE" block appended by
         value_catalog (e.g. `Assure.gender: female, male`).
      2. Registry descriptions containing quoted literals
         (e.g. `gender: STRING — Genre : 'female' ou 'male'`).
    """
    props: set[str] = set()
    text = (schema or "").strip()
    if not text:
        return props

    if _ENUM_HINTS_MARKER in text:
        block = text.split(_ENUM_HINTS_MARKER, 1)[1]
        for line in block.splitlines():
            match = _ENUM_HINTS_KEY_RE.match(line)
            if match:
                props.add(match.group(1).lower())

    for line in text.splitlines():
        match = _REGISTRY_PROP_RE.match(line)
        if match and match.group(1) not in _REGISTRY_FREE_TEXT_KEYS:
            props.add(match.group(1).lower())

    return props


def _strip_enum_hints(schema: str) -> str:
    text = (schema or "").strip()
    if _ENUM_HINTS_MARKER not in text:
        return text
    return text.split(_ENUM_HINTS_MARKER, 1)[0].rstrip()


def _truncate_block(text: str, *, max_chars: int | None) -> str:
    compact = (text or "").strip()
    if not compact or not max_chars or len(compact) <= max_chars:
        return compact
    trailer = "\n... (schema truncated for smaller-context model)"
    budget = max(0, max_chars - len(trailer))
    lines: list[str] = []
    total = 0
    for line in compact.splitlines():
        candidate = line if not lines else "\n" + line
        if total + len(candidate) > budget:
            break
        lines.append(line)
        total += len(candidate)
    truncated = "\n".join(lines).rstrip()
    return f"{truncated}{trailer}" if truncated else compact[:budget].rstrip() + trailer

# Rule 13b is dynamic (exact-match set is built from the schema at call time).
_TEXT_FILTERS_RULE_TEMPLATE = """\
 13b. TEXT FILTERS & INSURERS:
      Properties with known DB values ({exact_list}):
      use EXACT match on the values listed in the schema.
      For free-form user-typed names/insurers/products, use lowercase fuzzy
      matching: `toLower(n.name) CONTAINS "term"`.
      Never invent values not present in the schema's known-value list."""


def _build_text_filters_rule(schema: str) -> str:
    exact = _extract_exact_match_properties(schema)
    if exact:
        exact_list = ", ".join(sorted(exact))
    else:
        exact_list = "none detected — treat all values as free-form"
    return _TEXT_FILTERS_RULE_TEMPLATE.format(exact_list=exact_list)


_HARD_RULES = """\
══════════════════════ HARD RULES ══════════════════════
Output ONLY raw Cypher. Zero explanation, zero markdown, zero backticks.

━━━━━ SCHEMA COMPLIANCE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Use ONLY labels present in AVAILABLE SCHEMA (the property registry).
  2. Use ONLY relationship types present in AVAILABLE SCHEMA.
  3. Use ONLY property names listed for each label in AVAILABLE SCHEMA.
     If absent: do NOT guess, translate, or invent it.
  3b. PROPERTY PLACEMENT: each property belongs to the node where the
      schema lists it — never on a neighboring node.
      ✗ bs.reste_plafond  → ✓ icc.reste_plafond
      ✗ a.plafond         → ✓ icc.plafond
      ✗ bs.adherent_id    → only if listed on BulletinSoin in schema

━━━ DATE FUNCTIONS (Neo4j Cypher only — no SQL/Python syntax) ━━━
  4. "ce mois-ci"        → date({year: date().year, month: date().month, day: 1})
  5. "cette année"       → date({year: date().year, month: 1, day: 1})
  6. "N derniers jours"  → date() - duration({days: N})
  7. "plus de 2 ans"     → compute age in a WITH clause, then filter:
      MATCH (bs:BulletinSoin)-[:CREATED_FOR]->(a:Assure)
      WITH bs, a, date().year - bs.validation_date.year AS age_years
      WHERE age_years > 2
      RETURN a.id AS assure_id, count(bs) AS nb_bs
      ✗ Do NOT use duration.between() — it requires DATETIME, not DATE.
  8. DATE COMPONENTS: to get a year or month, access properties directly:
     `date.year` or `date.month` (e.g. `validation_date.month`).
     ✗ NEVER use SQL functions like `month(date)` or `date_part(month, date)`.
     Do NOT use technical ingestion metadata like `created_at` as the care date.

━━━━━ WHERE PLACEMENT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  9. WHERE is valid ONLY after: MATCH, OPTIONAL MATCH, or WITH.
     ✗ NEVER after RETURN. ✗ NEVER as first clause.
     ✗ NEVER directly after UNWIND — always insert WITH first:
        UNWIND list AS item
        WITH item
        WHERE item.x > 0   ← now valid
        RETURN item

━━━ MEMORY-SAFE PATTERNS (CRITICAL 16MB LIMIT) ━━━━━━━━━━━━━━━
 10. The database has a strict 16MB transaction limit.
     ✗ NEVER use `collect(node)` with whole nodes.
     ✗ NEVER do `collect(bs)` or `collect(a)`.
     ✓ ALWAYS collect ONLY the necessary IDs or scalar values: `collect({id: a.id, val: x})`.
     ✓ ALWAYS compute aggregations (sum, avg, count) BEFORE collecting data.
     ✓ Add `LIMIT` early if you don't have a strict `WHERE` date filter.
 11. For OPTIONAL MATCH on large graphs, add LIMIT before the optional part
     or use EXISTS {} instead when only checking existence.

━━━━━ FILTERING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 12. Add WHERE filters ONLY for constraints the user EXPLICITLY stated.
      ✗ Never add active=true or state=X unless the user asked for it.
      Before finalizing, verify that every explicit user constraint is present.
 13. Every numeric threshold in the question MUST appear in WHERE.
{__TEXT_FILTERS_RULE__}

━━━ ALIASES — MANDATORY ON EVERY COLUMN ━━━━━━━━━━━━━━━━━━━━━
 14. MANDATORY ALIAS: Every returned column MUST have an explicit, clean AS
     alias (e.g., RETURN a.id AS assure_id). Never return raw dot-notation.

━━━ RESULT SHAPE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 15. Never return whole nodes: ✗ RETURN a → ✓ RETURN a.id AS assure_id, …
 16. List queries: add ORDER BY + LIMIT 50 unless user asked for ALL rows.
 16b. AGGREGATION-ONLY queries (RETURN avg(...), sum(...), count(...) with
      NO per-entity rows) MUST NOT have LIMIT. LIMIT is for list/row queries
      only — it would truncate an aggregate to a single wrong value.
 17. Add LIMIT to prevent memory errors on potentially large result sets.

━━━ SINGLE STATEMENT ONLY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 23. Output EXACTLY ONE Cypher statement. Never emit two or more separate
     queries (e.g. a list query followed by a blank line and a stats query).
     ✗ MATCH ... RETURN ...  (blank line)  WITH ... MATCH ... RETURN ...
     If the user wants BOTH a list AND aggregates (counts, sums, averages):
     - prefer ONE aggregation query that returns the stats, OR
     - collect the list rows and aggregate in the SAME query, e.g.
       MATCH ... WITH collect({...}) AS rows, count(*) AS nb RETURN rows, nb.
     A second standalone MATCH/WITH block will be rejected as a multi-statement
     error. No semicolons, no blank-line-separated queries.

━━━ AGGREGATION (Cypher, not SQL) ━━━━━━━━━━━━━━━━━━━━━━━━━━━
 18. Never use GROUP BY / HAVING.
     Threshold: MATCH … WITH entity, count(x) AS cnt WHERE cnt > N RETURN …
 18b. NEVER count paths directly inside functions like `count((a)-[:R]->(b))`.
       Instead, use `size((a)-[:R]->(b))` or do a standard MATCH and count the
       entities: `WITH a, count(b) AS cnt`.

━━━ STRICT RELATIONSHIP DIRECTIONS ━━━━━━━━━━━━━━━━━━━━━━━━━
 19. NEVER reverse the direction of relationships. Pay strict attention to the arrows (-> and <-).
      ✗ BAD: (a:Assure)-[:CREATED_FOR]->(bs:BulletinSoin)
      ✓ GOOD: (bs:BulletinSoin)-[:CREATED_FOR]->(a:Assure)
      ✗ BAD: (a:Assure)-[:DEPENDENT_OF]->(b:Beneficiaire)
      ✓ GOOD: (b:Beneficiaire)-[:DEPENDENT_OF]->(a:Assure)
      ✗ BAD: (a:Assure)-[:COVERS]->(ic:InsuranceContract)
      ✓ GOOD: (ic:InsuranceContract)-[:COVERS]->(a:Assure)
      ✗ BAD: (:BulletinSoin)-[:BELONGS_TO_BS]->(:BulletinSoinPrestation)
      ✓ GOOD: (:BulletinSoinPrestation)-[:BELONGS_TO_BS]->(:BulletinSoin)
      ✗ BAD: (:BulletinSoinPrestation)-[:CREATED_UNDER]->(:BulletinSoinPrestationDetail)
      ✓ GOOD: (:BulletinSoinPrestationDetail)-[:CREATED_UNDER]->(:BulletinSoinPrestation)
      ✗ BAD: (:Product)-[:USES_PRODUCT]->(:BulletinSoinPrestationDetail)
      ✓ GOOD: (:BulletinSoinPrestationDetail)-[:USES_PRODUCT]->(:Product)

━━━ RETURN & AGGREGATION STRICTNESS ━━━━━━━━━━━━━━━━━━━━━━━━━
 20. RETURN EXACTLY ALL THE COLUMNS IMPLICATED BY THE QUESTION.
      If the question asks for "state", "num_bs", "date", return ALL of them.
 21. When asking for "Moyenne" (Average), PROPORTIONS, or RATIOS, ALWAYS use
      OPTIONAL MATCH for the items being counted so entities with 0 items are
      included in the average/ratio.
      ✓ MATCH (a:Assure) OPTIONAL MATCH (b:Beneficiaire)-[:DEPENDENT_OF]->(a) WITH a, count(b) AS nb RETURN avg(nb)

━━━ DATE SERIALIZATION (JSON transport requirement) ━━━━━━━━━
 22. Any property of type DATE, DATETIME, LOCALDATE, or LOCALDATETIME returned
      in a RETURN clause MUST be wrapped in toString(). Neo4j temporal types
      serialize as empty objects `{}` over JSON — toString() guarantees
      human-readable ISO strings.
      ✗ RETURN a.date_radiation
      ✓ RETURN toString(a.date_radiation) AS date_radiation
      ✗ RETURN bs.validation_date
      ✓ RETURN toString(bs.validation_date) AS validation_date
      This applies to EVERY date-type value in the RETURN clause.
═══════════════════════════════════════════════════════════"""

_SOFT_NOTES = """\
──────────────────────── NOTES ─────────────────────────
VOCABULARY & BUSINESS LOGIC MAPPING:
  - "date" / "ce mois-ci" / "cette année" (for claims) → ALWAYS use `bs.validation_date`. Use `p.date_prestation` only when specifically asked about the prestation date.
  - "adhérent 1426" / "adherent 1426" / "id 1426" → `a.id = 1426` on Assure.
  - "montant" / "dépense" / "déclaré" → ALWAYS use `total_dep`. NEVER use `montant_depense` (on BS, this field does not exist).
  - "prise en charge" / "PEC" → ALWAYS use `total_pec` on BulletinSoin. On prestation/detail lines, `montant_depense` / `montant_pec` exist — sum them.
  - "attente" / "en cours" → `state = 'draft'`. NEVER `state_prestation = 'attente'`.
  - "actif" (assuré) → `active = true`. NEVER `state = 'actif'`.
  - "actif" (assureur) → tous les assureurs sont actifs par défaut — NE PAS filtrer sur `active=true` (propriété absente de Assureur).
  - "radié" → `is_radiated = true` ET `date_radiation IS NOT NULL`.
  - "plafond global" / "général" / "total" (sans spécialité) → `icc.plafond` et `icc.reste_plafond` sur InsuranceContractConsommation.
  - "plafond <catégorie>" (hospitalisation, dentaire, optique, pharmacie) → `iccp.plafond` et `iccp.reste` sur InsuranceContractConsommationPlafond, joint via `(iccp)-[:CEILING_OF_CHAPTER]->(chap:InsuranceOfferChapitre)` filtré sur `toLower(chap.name) CONTAINS "..."`.
  - "nom de l'assureur" (Star, BH, Maghrebia) → lien vers le nœud Assureur et filtrer `toLower(assureur.name) CONTAINS "..."`. ✗ NEVER filter on `icc.name`, `ic.name`, `io.name`.

VALUE MAPPING:
  - "femme" / "F" → `gender = 'female'` ; "homme" / "M" → `gender = 'male'`. ✗ NEVER "F"/"M" littéraux.

DCI / MOLECULES:
  Path: (:Product)-[:HAS_DCI]->(:DCI)
  Filter with `drug_description_french_dci` or `drug_description` on the DCI node.
  Most-prescribed DCI: count via BulletinSoinPrestationDetail → Product → DCI.
  ✗ NEVER use LettresCle as proxy for DCI.

DISEASES & PATHOLOGIES:
  - No `Condition`/`Disease` label exists. Chronic: `icc.is_chronique = true`.
  - Specific disease (diabète, hypertension) via DCI indications:
    MATCH (det:BulletinSoinPrestationDetail)-[:USES_PRODUCT]->(p:Product)-[:HAS_DCI]->(dci:DCI)
    WHERE toLower(dci.drug_description_french_dci) CONTAINS "diabete"
       OR toLower(dci.indications) CONTAINS "diabete"

BORDEREAU:
  Label is exactly "Bordereau". Path: (:BulletinSoin)-[:IN_BORDEREAU]->(:Bordereau)

ZERO-ROW PREVENTION:
  Filters like 'ce mois-ci' or 'active=true' may return 0 rows if the DB has no
  matching data. If the question does not explicitly require a time filter,
  prefer a wider range (last 3 months) or omit the date filter entirely.
  For booleans (handicape, active) that may not exist on all nodes, use
  OPTIONAL or remove the filter if not critical.

PRODUCT TYPES & NATURE:
  Product has NO `nature` property. Filter via relationships:
  - Category:    (:Product)-[:IN_CATEGORY]->(:ProductCategory)
  - Family:      (:Product)-[:IN_FAMILLE]->(:ProductFamille)
  - Nature/Type: (:Product)-[:HAS_NATURE]->(:ProductNature)
  For "pharmaceutique"/"pharmacie"/"médicament", use multiple CONTAINS
  conditions on `pn.name`. ✗ NEVER p.nature / p.type / p.category / p.famille.
────────────────────────────────────────────────────────────"""


def _resolve_few_shots(compact: bool, few_shot_category: str | None) -> str:
    if compact:
        return _COMPACT_FEW_SHOTS
    if few_shot_category and few_shot_category in FEW_SHOT_MODULES:
        return FEW_SHOT_MODULES[few_shot_category].FEW_SHOTS.strip()
    return FEW_SHOTS


def build_cypher_system_prompt(
    schema: str,
    validation_error: str | None,
    *,
    compact: bool = False,
    max_schema_chars: int | None = None,
    include_examples: bool = True,
    few_shot_category: str | None = None,
) -> str:
    schema_block = (schema or "").strip()
    if compact:
        schema_block = _strip_enum_hints(schema_block)
    schema_block = _truncate_block(schema_block, max_chars=max_schema_chars)

    few_shots_block = _resolve_few_shots(compact, few_shot_category)

    # --- Injection de l'erreur en tête de prompt ---
    retry_header = ""
    if validation_error:
        retry_header = f"\n⚠️ CRITICAL CORRECTION REQUIRED:\n{format_validation_retry_block(validation_error)}\n"

    intro = (
        "You are a Neo4j Cypher expert for a health-insurance graph database.\n"
        "The user writes in French or English; always output valid Cypher.\n"
        f"{retry_header}"  # Placé ici pour une visibilité maximale par l'attention du LLM
    )

    schema_section = (
        "══════════════════════ AVAILABLE SCHEMA ═══════════════════════\n"
        f"{schema_block}\n"
        "═══════════════════════════════════════════════════════════════"
    )

    examples_section = ""
    if include_examples:
        examples_section = (
            "\n══════════════════════ EXAMPLES ═══════════════════════\n"
            f"{few_shots_block}\n"
            "════════════════════════════════════════════════════════\n"
        )

    soft = "" if compact else f"\n{_SOFT_NOTES}\n"

    hard_rules = _HARD_RULES.replace(
        "{__TEXT_FILTERS_RULE__}",
        _build_text_filters_rule(schema_block),
    )

    return (
        f"{intro}\n"
        f"{schema_section}\n\n"
        f"{hard_rules}\n"
        f"{soft}"
        f"{examples_section}"
    )
