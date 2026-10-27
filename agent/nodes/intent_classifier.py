from __future__ import annotations

"""Intelligent entry-point node.

Decides, per question, whether a database query is actually needed. The LLM
routes the question to either:
  - "db"  -> generate Cypher and run the graph pipeline (data question)
  - "chat" -> answer directly with the LLM, no Cypher, no charts
             (greetings, chit-chat, off-topic, vague questions)

This avoids wasting a Cypher call (and producing phantom charts) for things
like "bonjour". If the LLM is unavailable, a cheap heuristic keeps behavior
sensible without hardcoding any answer text.
"""

import json
import logging

from agent.state import AgentState
from agent.trace_util import step
from llm.router import get_provider

logger = logging.getLogger(__name__)

_PROMPT = """You are the router for a health-insurance graph assistant.
Decide if the user message requires querying the Neo4j database.

Answer with a JSON object ONLY: {"route": "db"} or {"route": "chat"}.

Use "db" when the message asks for specific data/facts that must come from the
database (counts, lists, comparisons, trends, lookups about clients, contracts,
claims, products, payments, etc.).

Use "chat" for anything that does NOT need stored data: greetings (bonjour,
salut, hello), thanks, small talk, questions about the assistant's capabilities,
or messages too vague to query.

Respond with JSON and nothing else."""

_GREETING_MARKERS = {
    "bonjour", "salut", "hello", "hi", "hey", "coucou", "bonsoir", "merci",
    "ça va", "ca va", "comment", "au revoir", "bye", "ok", "d'accord", "okay",
}


def _heuristic_route(question: str) -> str:
    words = set(w.strip(".,!?;:") for w in question.lower().split())
    if words & _GREETING_MARKERS:
        return "chat"
    # A data question usually carries a noun/interrogative about entities.
    data_markers = {
        "combien", "quels", "quelles", "quel", "quelle", "liste", "clients",
        "client", "contrat", "contrats", "sinistre", "sinistres", "prime",
        "primes", "produit", "produits", "paiement", "paiements", "claim",
        "claims", "contract", "contracts", "payment", "payments", "how many",
        "show", "find", "name", "names", "total",
    }
    if words & data_markers:
        return "db"
    # Default: if we can't tell, prefer querying the DB (safe for data bots).
    return "db"


def _detect_language(text: str) -> str:
    french_markers = {
        "quels", "quelles", "quel", "quelle", "combien", "les", "des", "ont",
        "été", "avec", "pour", "dans", "sur", "bonjour", "salut", "merci",
    }
    words = set(text.lower().split())
    return "fr" if words & french_markers else "en"


def run(state: AgentState) -> dict:
    # ── AG-UI / CopilotKit: sync messages → question ──
    question = state.get("question", "")
    if not question and state.get("messages"):
        from langchain_core.messages import HumanMessage
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                question = msg.content
                break

    # ── PII redaction ──
    from config.settings import get_settings
    if get_settings().PII_FILTER_ENABLED:
        from guardrails.pii_detector import detect_and_redact_pii
        cleaned, redactions = detect_and_redact_pii(question)
        if redactions:
            logger.info("PII redacted %d item(s) from user message", len(redactions))
            question = cleaned

    # ── Session management ──
    session_id = state.get("session_id")
    if session_id:
        try:
            from memory.session_manager import ensure_session, save_session
            session = ensure_session(session_id)
            if session.get("cancelled"):
                session["cancelled"] = False
                save_session(session)
        except Exception:
            pass

    # Extract the actual user message (last line after "Current user question:")
    user_msg = question.strip()
    if "Current user question:" in user_msg:
        user_msg = user_msg.rsplit("Current user question:", 1)[-1].strip()

    route = "db"

    # Slash commands bypass intent entirely and go straight to the resolver.
    if user_msg.startswith("\\"):
        return {
            "trace_steps": [
                step("intent_classifier", "route_shortcut", route="shortcut"),
            ],
        }

    try:
        provider = get_provider()
        raw = provider.synthesize_answer(
            system_prompt=_PROMPT,
            question=question,
            data_payload="",
        )
        parsed = json.loads(raw)
        decided = str(parsed.get("route", "")).strip().lower()
        if decided in {"db", "chat"}:
            route = decided
    except Exception as exc:
        logger.warning("Intent classifier LLM unavailable (%s), using heuristic", exc)
        route = _heuristic_route(question)

    if route == "chat":
        answer = _direct_answer(question)
        return {
            "question": question,
            "final_answer": answer,
            "trace_steps": [
                step("intent_classifier", "route_chat", route="chat"),
            ],
        }

    return {
        "question": question,
        "trace_steps": [
            step("intent_classifier", "route_db", route="db"),
        ],
    }


def _direct_answer(question: str) -> str:
    """Generate a natural direct reply without touching the database."""
    lang = _detect_language(question)
    try:
        provider = get_provider()
        system = (
            "You are a helpful assistant for a health-insurance graph system. "
            "Reply naturally in the user's language. Do NOT write any database "
            "query and do NOT invent data. If asked what you can do, briefly "
            "describe that you can answer questions about clients, contracts, "
            "claims, products and payments."
        )
        return provider.synthesize_answer(
            system_prompt=system,
            question=question,
            data_payload="",
        )
    except Exception as exc:
        logger.warning("Direct answer LLM unavailable (%s)", exc)
        if lang == "fr":
            return "Bonjour ! Je suis votre assistant sur les données d'assurance santé. Posez-moi une question sur les clients, contrats, sinistres ou paiements pour obtenir des résultats."
        return "Hello! I'm your health-insurance data assistant. Ask me about clients, contracts, claims or payments to get results."
