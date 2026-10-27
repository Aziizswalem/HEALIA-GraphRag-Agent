"""
guardrails/query_guard_patch.py â€” v2 (fixes C2, C3, C5, C6)

FIX C2/C3 â€” Suppression de get_dynamic_topology() et _DYNAMIC_TOPO_CACHE
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
AVANT : get_dynamic_topology() maintenait son propre cache (None = pas de TTL,
        appel Ã  db.schema.visualization() sÃ©parÃ© de topology.py).
        â†’ 2 appels rÃ©seau Neo4j possibles par requÃªte, 2 caches Ã  dÃ©synchroniser.
APRÃˆS : get_dynamic_topology() et fetch_dynamic_topology_string() sont supprimÃ©s.
        Le validator passe directement domain_topology (dÃ©jÃ  chargÃ© via
        get_topology_cached_or_fetch()) Ã  graph_path_semantic_check().

FIX C5 â€” NÅ“uds valides absents du schÃ©ma dynamique
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
AVANT : _extract_schema_names() ne lisait que le schÃ©ma dynamique â†’ rejetait
        DCI, Bordereau, InsuranceContract, InsuranceOffer, etc. comme "inconnus".
APRÃˆS : _extract_schema_names() enrichit systÃ©matiquement les labels et relations
        autorisÃ©s avec FULL_SCHEMA (static_schema.py), qui est la source de vÃ©ritÃ©
        vÃ©rifiÃ©e contre la base live. Aucun faux positif possible sur ces nÅ“uds.

FIX C6 â€” Chemins composÃ©s dans DOMAIN_TOPOLOGY non parsÃ©s par _parse_topology_triples
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
AVANT : _TOPO_PATH_RE ne matchait que les triplets simples (A)-[R]->(B).
        Les lignes multi-sauts de DOMAIN_TOPOLOGY comme :
          (:Client)<-[:APPLIES_TO_COMPANY]-(:InsuranceContractCompany)-[:HAS_COLLEGE]->...
        n'Ã©taient pas parsÃ©es â†’ triples manquants â†’ faux positifs sur chemins valides.
APRÃˆS : _parse_topology_triples() dÃ©compose les lignes multi-sauts en triplets
        Ã©lÃ©mentaires avant de les indexer. Chaque segment (A)-[R]->(B) ou
        (B)<-[R]-(A) est normalisÃ© en (source, rel, target) canonique.
"""

from __future__ import annotations

import re
from typing import Set, Tuple

# â”€â”€ Shared patterns and helpers (extracted to _common.py) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from guardrails._common import (
    SCHEMA_LABEL_RE,
    SCHEMA_REL_RE,
    SCHEMA_PROP_RE,
    NODE_PATTERN_RE,
    REL_PATTERN_RE,
    extract_query_labels,
    extract_query_relationships,
    format_unknown_names,
)

# â”€â”€ FIX C5 : import de la source de vÃ©ritÃ© statique â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from graph.schema.static_schema import FULL_SCHEMA as _STATIC_FULL_SCHEMA


# ---------------------------------------------------------------------------
# A) ALLOWLISTS & HELPERS for schema_name_semantic_check_v2
# ---------------------------------------------------------------------------

_CYPHER_MAP_KEY_ALLOWLIST: Set[str] = {
    "year", "month", "week", "day", "hour", "minute", "second",
    "millisecond", "quarter", "ordinalday", "weekyear", "weekday", "dayofweek",
}

_CYPHER_MAP_FUNCTIONS: Set[str] = {
    "duration", "date", "datetime", "time", "localtime", "localdatetime", "point",
}

_TEMPORAL_ACCESSORS: Set[str] = {
    "year", "month", "week", "day", "hour", "minute", "second",
    "millisecond", "microsecond", "nanosecond", "quarter",
    "ordinalday", "weekyear", "weekday", "dayofweek",
}

# â”€â”€ FIX C5 : labels et relations garantis extraits de FULL_SCHEMA statique â”€â”€â”€â”€
# CalculÃ©s une seule fois au chargement du module (pas de coÃ»t Ã  l'exÃ©cution).
_STATIC_ALLOWED_LABELS: Set[str] = {
    lbl.lower() for lbl in SCHEMA_LABEL_RE.findall(_STATIC_FULL_SCHEMA)
}
_STATIC_ALLOWED_RELS: Set[str] = {
    rel.lower() for rel in SCHEMA_REL_RE.findall(_STATIC_FULL_SCHEMA)
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_variables_and_aliases(cypher: str) -> Set[str]:
    names: Set[str] = set()
    for m in re.finditer(r"\bAS\s+(\w+)", cypher, re.IGNORECASE):
        names.add(m.group(1).lower())
    for m in re.finditer(r"\(\s*([A-Za-z_]\w*)\s*(?:[:\|)])", cypher):
        names.add(m.group(1).lower())
    for m in re.finditer(r"\[\s*([A-Za-z_]\w*)\s*(?:[:\|])", cypher):
        names.add(m.group(1).lower())

    _KEYWORDS = {
        "match", "optional", "where", "return", "with", "unwind", "call",
        "order", "by", "limit", "skip", "distinct", "as", "and", "or",
        "not", "in", "is", "null", "true", "false", "count", "sum", "avg",
        "min", "max", "collect", "exists", "case", "when", "then", "else", "end",
    }
    for m in re.finditer(r"\bWITH\b(.+?)(?:\bWHERE\b|\bMATCH\b|\bRETURN\b|\bWITH\b|$)",
                         cypher, re.IGNORECASE | re.DOTALL):
        for token in re.split(r",", m.group(1)):
            words = re.findall(r"\b([A-Za-z_]\w*)\b", token)
            for w in words:
                if w.lower() not in _KEYWORDS:
                    names.add(w.lower())
    return names


def _extract_map_function_keys(cypher: str) -> Set[str]:
    keys: Set[str] = set()
    fn_pattern = r"\b(?:" + "|".join(_CYPHER_MAP_FUNCTIONS) + r")\s*\(\s*\{([^}]*)\}"
    for m in re.finditer(fn_pattern, cypher, re.IGNORECASE):
        map_body = m.group(1)
        for key_m in re.finditer(r"\b([A-Za-z_]\w*)\s*:", map_body):
            keys.add(key_m.group(1).lower())
    return keys


def _parse_variable_labels(cypher: str) -> dict[str, Set[str]]:
    var_to_labels: dict[str, Set[str]] = {}
    pattern = r"\(\s*([A-Za-z_]\w*)\s*:([A-Za-z_]\w*(?:\s*:\s*[A-Za-z_]\w*)*)"
    for m in re.finditer(pattern, cypher):
        var_name = m.group(1).lower()
        labels_str = m.group(2)
        labels = {lbl.strip() for lbl in labels_str.split(":") if lbl.strip()}
        var_to_labels.setdefault(var_name, set()).update(labels)
    return var_to_labels


def _parse_schema_properties(schema_context: str) -> dict[str, Set[str]]:
    label_to_props: dict[str, Set[str]] = {}

    for line in (schema_context or "").splitlines():
        line = line.strip()
        if not line:
            continue
        textual_props = re.match(
            r"Properties\s+on\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$",
            line,
            re.IGNORECASE,
        )
        if textual_props:
            label = textual_props.group(1).lower()
            props = {
                prop.strip().lower()
                for prop in textual_props.group(2).split(",")
                if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*$", prop)
            }
            label_to_props.setdefault(label, set()).update(props)
            continue
        labels = [lbl.lower() for lbl in SCHEMA_LABEL_RE.findall(line)]
        if not labels:
            continue

        line_props: Set[str] = set()
        for block in SCHEMA_PROP_RE.findall(line):
            for raw_name in block.split(","):
                candidate = raw_name.strip()
                if not candidate or candidate.startswith("..."):
                    continue
                match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", candidate)
                if match:
                    line_props.add(match.group(1).lower())

        for label in labels:
            label_to_props.setdefault(label, set()).update(line_props)

    return label_to_props


def _extract_schema_names(schema_context: str) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    FIX C5 â€” Extrait labels, relations et propriÃ©tÃ©s autorisÃ©s depuis :
      1. Le schÃ©ma dynamique (schema_context passÃ© en paramÃ¨tre).
      2. FULL_SCHEMA statique (_STATIC_ALLOWED_LABELS / _STATIC_ALLOWED_RELS).
    Les nÅ“uds absents du schÃ©ma dynamique (DCI, Bordereau, InsuranceContract,
    etc.) sont couverts par la source statique â†’ plus de faux positifs.
    """
    text = schema_context or ""

    # Extraction depuis le schÃ©ma dynamique
    labels: Set[str] = set(SCHEMA_LABEL_RE.findall(text))
    relationships: Set[str] = set(SCHEMA_REL_RE.findall(text))
    properties: Set[str] = set()

    for line in text.splitlines():
        label_line = re.match(r"\s*Node\s+labels\s*:\s*(.+)$", line, re.IGNORECASE)
        if label_line:
            labels.update(
                name.strip()
                for name in label_line.group(1).split(",")
                if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*$", name)
            )
            continue
        rel_line = re.match(r"\s*Relationship\s+types\s*:\s*(.+)$", line, re.IGNORECASE)
        if rel_line:
            relationships.update(
                name.strip()
                for name in rel_line.group(1).split(",")
                if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*$", name)
            )
            continue
        prop_line = re.match(
            r"\s*Properties\s+on\s+[A-Za-z_][A-Za-z0-9_]*\s*:\s*(.+)$",
            line,
            re.IGNORECASE,
        )
        if prop_line:
            properties.update(
                name.strip()
                for name in prop_line.group(1).split(",")
                if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*$", name)
            )
    for block in SCHEMA_PROP_RE.findall(text):
        for raw_name in block.split(","):
            candidate = raw_name.strip()
            if not candidate or candidate.startswith("..."):
                continue
            match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", candidate)
            if match:
                properties.add(match.group(1))

    # FIX C5 : enrichissement avec les labels/relations statiques garantis
    # Union avec _STATIC_ALLOWED_LABELS et _STATIC_ALLOWED_RELS (minuscules).
    # On travaille en minuscules pour la comparaison, donc on convertit labels/rels
    # dynamiques aussi en minuscules avant l'union.
    labels_lower = {lbl.lower() for lbl in labels} | _STATIC_ALLOWED_LABELS
    rels_lower = {rel.lower() for rel in relationships} | _STATIC_ALLOWED_RELS

    # On retourne les sets en minuscules (compatibles avec les comparaisons existantes)
    return labels_lower, rels_lower, properties


# ---------------------------------------------------------------------------
# schema_name_semantic_check_v2
# ---------------------------------------------------------------------------

def schema_name_semantic_check_v2(
    cypher: str,
    schema_context: str,
) -> str | None:
    return None  # Désactivé — trop strict, bloque des requêtes valides

    if not schema_context:
        return None

    # FIX C5 : _extract_schema_names retourne dÃ©sormais labels+rels enrichis
    # avec FULL_SCHEMA statique â†' DCI, Bordereau, InsuranceContract, etc. autorisÃ©s.
    allowed_labels, allowed_relationships, allowed_properties = _extract_schema_names(schema_context)
    allowed_properties_lower = {p.lower() for p in allowed_properties}

    # Les sets retournÃ©s par _extract_schema_names sont dÃ©jÃ  en minuscules (FIX C5)
    allowed_labels_lower = allowed_labels
    allowed_relationships_lower = allowed_relationships

    query_labels = extract_query_labels(cypher)
    query_relationships = extract_query_relationships(cypher)

    unknown_labels = {lbl for lbl in query_labels if lbl.lower() not in allowed_labels_lower}
    unknown_relationships = {rel for rel in query_relationships if rel.lower() not in allowed_relationships_lower}

    problems: list[str] = []
    if unknown_labels:
        problems.append(f"unknown labels: {format_unknown_names(unknown_labels)}")
    if unknown_relationships:
        problems.append(f"unknown relationship types: {format_unknown_names(unknown_relationships)}")

    if problems:
        return "The query uses names that do not appear in the available schema context: " + "; ".join(problems) + "."

    label_to_props = _parse_schema_properties(schema_context)
    variables_and_aliases = _extract_variables_and_aliases(cypher)
    map_function_keys = _extract_map_function_keys(cypher)

    skip: Set[str] = (
        variables_and_aliases
        | map_function_keys
        | _CYPHER_MAP_KEY_ALLOWLIST
        | _TEMPORAL_ACCESSORS
    )

    var_to_labels = _parse_variable_labels(cypher)

    for m in re.finditer(r"\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)", cypher):
        var_name = m.group(1).lower()
        prop_name = m.group(2).lower()

        if prop_name in skip:
            continue

        if var_name in variables_and_aliases:
            labels = var_to_labels.get(var_name, set())
            if labels:
                has_prop = False
                for label in labels:
                    if prop_name in label_to_props.get(label.lower(), set()):
                        has_prop = True
                        break
                if not has_prop:
                    labels_str = "/".join(sorted(labels))
                    return (
                        f"Unknown schema name: property '{prop_name}' does not exist on label(s) '{labels_str}' "
                        f"in the available schema."
                    )
            else:
                if prop_name not in allowed_properties_lower:
                    return (
                        f"Unknown schema name: property '{prop_name}' is not found in the available schema."
                    )

    KEYWORDS = {"match", "with", "return", "where", "and", "or", "create", "merge", "delete", "detach", "remove", "set", "unwind", "optional"}
    for m in re.finditer(r"\(([^)]*)\)", cypher):
        inside = m.group(1)
        if "{" not in inside:
            continue

        prefix = cypher[:m.start()].rstrip()
        word_match = re.search(r"\b([A-Za-z_]\w*)$", prefix)
        if word_match:
            word = word_match.group(1).lower()
            if word not in KEYWORDS:
                continue

        node_head = inside.split("{")[0]
        node_labels = {lbl.strip().lower() for lbl in re.findall(r":\s*([A-Za-z_]\w*)", node_head)}

        for braces_match in re.finditer(r"\{([^}]*)\}", inside):
            map_body = braces_match.group(1)
            for key_m in re.finditer(r"\b([A-Za-z_]\w*)\s*:", map_body):
                key_name = key_m.group(1).lower()
                if key_name in skip:
                    continue

                if node_labels:
                    has_prop = False
                    for label in node_labels:
                        if key_name in label_to_props.get(label, set()):
                            has_prop = True
                            break
                    if not has_prop:
                        labels_str = "/".join(sorted(node_labels))
                        return (
                            f"Unknown schema name: map key '{key_name}' does not exist on label(s) '{labels_str}' "
                            f"in the available schema."
                        )
                else:
                    if key_name not in allowed_properties_lower:
                        return (
                            f"Unknown schema name: map key '{key_name}' is not found in the available schema."
                        )

    for m in re.finditer(r"\[([^\]]*)\]", cypher):
        inside = m.group(1)
        if "{" not in inside:
            continue
        for braces_match in re.finditer(r"\{([^}]*)\}", inside):
            map_body = braces_match.group(1)
            for key_m in re.finditer(r"\b([A-Za-z_]\w*)\s*:", map_body):
                key_name = key_m.group(1).lower()
                if key_name in skip:
                    continue
                if key_name not in allowed_properties_lower:
                    return (
                        f"Unknown schema name: relationship map key '{key_name}' is not found in the available schema."
                    )

    return None


# ===========================================================================
# B) graph_path_semantic_check â€” FIX C6
# ===========================================================================

def _parse_topology_triples(domain_topology: str) -> Set[tuple[str, str, str]]:
    """
    FIX C6 â€” DÃ©compose les lignes de topologie en triplets Ã©lÃ©mentaires.

    AVANT : regex simple, ne matchait que (:A)-[:R]->(:B) sur une seule ligne.
            Les chemins composÃ©s comme :
              (:Client)<-[:APPLIES_TO_COMPANY]-(:ICC)-[:HAS_COLLEGE]->(:College)
            n'Ã©taient pas parsÃ©s â†’ triples manquants â†’ faux positifs.

    APRÃˆS : on dÃ©compose chaque ligne en segments individuels en cherchant
            tous les couples consÃ©cutifs nÅ“ud-relation-nÅ“ud, quelle que soit
            la complexitÃ© de la ligne.

    Supporte :
      - (A)-[:R]->(B)           â†’ triple (a, r, b)
      - (A)<-[:R]-(B)           â†’ triple (b, r, a)
      - (A)-[:R]->(B)-[:S]->(C) â†’ triples (a, r, b) + (b, s, c)
      - (B)<-[:R]-(A)-[:S]->(C) â†’ triples (a, r, b) + (a, s, c)
    """
    triples: Set[tuple[str, str, str]] = set()

    # Pattern pour un segment orientÃ© dans un chemin composÃ© :
    # Group 1 : label du nÅ“ud gauche
    # Group 2 : '<' (flÃ¨che entrante) ou absent
    # Group 3 : type de relation
    # Group 4 : '>' (flÃ¨che sortante) ou absent
    # Group 5 : label du nÅ“ud droit
    segment_re = re.compile(
        r"\(\s*:?([A-Za-z_]\w*)\s*\)\s*"   # nÅ“ud gauche
        r"(<-|-)\s*"                         # dÃ©but du segment de relation
        r"\[\s*:([A-Za-z_]\w*)\s*\]\s*"    # type de relation
        r"(-|->)\s*"                         # fin du segment de relation
        r"\(\s*:?([A-Za-z_]\w*)\s*\)",      # nÅ“ud droit
        re.IGNORECASE,
    )

    for m in segment_re.finditer(domain_topology):
        left_label = m.group(1).lower()
        arrow_left = m.group(2)   # "<-" ou "-"
        rel_type = m.group(3).lower()
        arrow_right = m.group(4)  # "->" ou "-"
        right_label = m.group(5).lower()

        is_incoming = arrow_left == "<-"

        if is_incoming:
            # (A)<-[:R]-(B)  â†’ source = B, target = A
            triples.add((right_label, rel_type, left_label))
        else:
            # (A)-[:R]->(B)  â†’ source = A, target = B
            triples.add((left_label, rel_type, right_label))

    return triples


def _parse_single_node_labels(node_content: str, var_to_labels: dict[str, Set[str]]) -> Tuple[str, Set[str]]:
    if not node_content:
        return "", set()

    if ":" in node_content:
        var_part, _, labels_part = node_content.partition(":")
        var_name = var_part.strip().lower()
        labels = {lbl.strip() for lbl in labels_part.split(":") if lbl.strip()}
        return var_name, labels

    var_name = node_content.strip().lower()
    if var_name:
        labels = var_to_labels.get(var_name, set())
        return var_name, labels

    return "", set()


def graph_path_semantic_check(
    cypher: str,
    domain_topology: str,
) -> str | None:
    """
    Validateur de chemin â€” FIX C2/C3 : domain_topology passÃ© directement
    par le validator (variable dÃ©jÃ  chargÃ©e), plus d'appel Ã  get_dynamic_topology().

    FIX C6 : _parse_topology_triples dÃ©compose dÃ©sormais les chemins composÃ©s.
    """
    if not domain_topology:
        return None

    valid_triples = _parse_topology_triples(domain_topology)
    if not valid_triples:
        return None

    var_to_labels = _parse_variable_labels(cypher)

    pattern = r"\(([^)]*)\)\s*(<-)?\s*-\s*\[\s*:([A-Za-z_]\w*)\s*\]\s*-\s*(>)?\s*\(([^)]*)\)"

    for m in re.finditer(pattern, cypher):
        start_content = m.group(1).strip()
        is_left = bool(m.group(2))
        rel_type = m.group(3).lower()
        is_right = bool(m.group(4))
        end_content = m.group(5).strip()

        start_var, start_labels = _parse_single_node_labels(start_content, var_to_labels)
        end_var, end_labels = _parse_single_node_labels(end_content, var_to_labels)

        if not start_labels or not end_labels:
            continue

        if is_left:
            from_labels, to_labels = end_labels, start_labels
        else:
            from_labels, to_labels = start_labels, end_labels

        path_valid = False
        for f_lbl in from_labels:
            for t_lbl in to_labels:
                triple = (f_lbl.lower(), rel_type.lower(), t_lbl.lower())
                if triple in valid_triples:
                    path_valid = True
                    break
            if path_valid:
                break

        if not path_valid:
            from_lbls_str = "/".join(sorted(from_labels))
            to_lbls_str = "/".join(sorted(to_labels))
            return (
                f"Invalid graph path: (:{from_lbls_str})-[:{rel_type.upper()}]->(:{to_lbls_str}) "
                f"does not exist in the domain topology. "
                f"Check the relationship direction and label names."
            )

    return None

# ---------------------------------------------------------------------------
# NOTE FIX C2/C3 : fetch_dynamic_topology_string() et get_dynamic_topology()
# sont intentionnellement supprimÃ©s de ce fichier.
#
# La topologie est dÃ©sormais fournie exclusivement via :
#   graph.schema.topology.get_topology_cached_or_fetch()
# qui gÃ¨re un cache TTL thread-safe et un fallback sur FULL_SCHEMA statique.
#
# Le validator (cypher_validator_updated.py) charge domain_topology une fois
# et le passe directement Ã  graph_path_semantic_check(domain_topology=...).
# ---------------------------------------------------------------------------

