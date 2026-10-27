from __future__ import annotations

"""Slash-command shortcuts for frequent insurance questions.

Lets a user bypass the LLM entirely for common lookups, e.g.:
  \\adherent 219018     -> client profile
  \\assureur Star       -> insurer overview
  \\contrat 123         -> contract detail
  \\sinistres 219018    -> member's bulletins de soin
  \\help                -> list available shortcuts

Each shortcut is a parameterized, pre-validated Cypher template plus a human
title. No LLM call is made; results are rendered through the deterministic
GenUI builder so charts are always faithful to the data.
"""
import re
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Shortcut:
    name: str
    description: str
    # regex with one capture group for the argument (None for no-arg commands)
    arg_pattern: str | None
    cypher: str
    title: str


_SHORTCUTS: dict[str, Shortcut] = {}


def _register(s: Shortcut) -> None:
    _SHORTCUTS[s.name] = s


# ── Argument-safe helpers ────────────────────────────────────────────────────
def _quote(value: str) -> str:
    """Escape a user-supplied string for safe Cypher embedding."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    return f'"{escaped}"'


def _int_arg(raw: str) -> str:
    """Coerce to int; raise if not a clean integer (prevents injection)."""
    try:
        return str(int(raw.strip()))
    except (TypeError, ValueError):
        raise ValueError(f"expected an integer id, got: {raw!r}")


# ── Shortcut definitions ─────────────────────────────────────────────────────
_register(
    Shortcut(
        name="adherent",
        description="Dashboard adherent complet : résumé, mensuel, disciplines, top prestataires (ex: \\adherent 219018)",
        arg_pattern=r"^\s*(\d+)\s*$",
        cypher="__ADHERENT_DASHBOARD__",
        title="Dashboard de l'adhérent",
    )
)

_register(
    Shortcut(
        name="contrat",
        description="Détail d'un contrat entreprise par id (ex: \\contrat 123)",
        arg_pattern=r"^\s*(\d+)\s*$",
        cypher=(
            "MATCH (icc:InsuranceContractCompany {id: __ID__}) "
            "RETURN icc.id AS contrat_id, icc.name AS nom_contrat, icc.state AS etat, "
            "toString(icc.date_start) AS date_debut, toString(icc.date_end) AS date_fin, "
            "icc.limit_age AS age_limite, icc.active AS actif, "
            "icc.company_id AS company_id, icc.assurance_id AS assureur_id, "
            "icc.offer_id AS offre_id"
        ),
        title="Contrat entreprise",
    )
)

_register(
    Shortcut(
        name="client",
        description="Dashboard client complet : résumé, mensuel, disciplines, top prestataires (ex: \\client 47)",
        arg_pattern=r"^\s*(\d+)\s*$",
        cypher="__CLIENT_DASHBOARD__",
        title="Dashboard Client",
    )
)

_register(
    Shortcut(
        name="sinistres",
        description="Bulletins de soin d'un adhérent par id (ex: \\sinistres 219018)",
        arg_pattern=r"^\s*(\d+)\s*$",
        cypher=(
            "MATCH (bs:BulletinSoin)-[:CREATED_FOR]->(c:Client {id: __ID__}) "
            "RETURN bs.num_bs AS num_bs, toString(bs.validation_date) AS date_validation, "
            "bs.total_dep AS total_depense, bs.total_pec AS total_pec, bs.state AS etat "
            "ORDER BY bs.validation_date DESC LIMIT 50"
        ),
        title="Bulletins de soin de l'adhérent",
    )
)

_HELP_TEXT = (
    "Raccourcis disponibles (tapez la commande suivie de l'argument) :\n"
    + "\n".join(
        f"  \\{s.name} — {s.description}" for s in _SHORTCUTS.values()
    )
    + "\n  \\help — affiche cette aide"
)


def get_shortcut(name: str) -> Shortcut | None:
    return _SHORTCUTS.get(name.lower())


def list_shortcut_names() -> list[str]:
    return sorted(_SHORTCUTS.keys())


def help_text() -> str:
    return _HELP_TEXT


def parse_shortcut(question: str) -> tuple[Shortcut, str] | None:
    """Return (shortcut, raw_arg) if the question is a valid slash command."""
    if not question.startswith("\\"):
        return None
    body = question[1:].strip()
    parts = body.split(None, 1)
    name = parts[0].lower() if parts else ""
    raw_arg = parts[1] if len(parts) > 1 else ""
    sc = get_shortcut(name)
    if sc is None:
        return None
    if sc.arg_pattern is None:
        return sc, ""
    if not re.match(sc.arg_pattern, raw_arg):
        raise ValueError(f"Argument invalide pour \\{sc.name}: {raw_arg!r}")
    return sc, raw_arg


def render_cypher(sc: Shortcut, raw_arg: str) -> str:
    """Safely substitute the user argument into the Cypher template."""
    if sc.name == "client":
        return _int_arg(raw_arg)  # returns just the ID as string
    if sc.name == "contrat" or sc.name == "sinistres":
        value = _int_arg(raw_arg)
        return sc.cypher.replace("__ID__", value)
    if sc.name == "assureur":
        return sc.cypher.replace("__NAME__", _quote(raw_arg.strip()))
    return sc.cypher
