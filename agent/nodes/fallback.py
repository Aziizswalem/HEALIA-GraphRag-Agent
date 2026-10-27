from agent.state import AgentState
from agent.trace_util import step

FALLBACK_FR = (
    "Je n'ai pas pu générer une requête valide pour répondre à votre question. "
    "Dernière erreur : {error}\n\n"
    "Essayez de reformuler en étant plus précis (ex: identifiant patient, période)."
)

FALLBACK_EN = (
    "I was unable to generate a valid query to answer your question. "
    "Last error: {error}\n\n"
    "Try rephrasing with more detail (e.g. a patient ID or a specific time period)."
)


def _detect_language(text: str) -> str:
    """Cheap heuristic: check for common French words."""
    french_markers = {"quels", "quelles", "quel", "quelle", "combien", "les", "des",
                      "quel", "ont", "été", "avec", "pour", "dans", "sur"}
    words = set(text.lower().split())
    return "fr" if words & french_markers else "en"


def run(state: AgentState) -> dict:
    last_error = state.get("validation_error", "unknown error")
    lang = _detect_language(state.get("question", ""))
    template = FALLBACK_FR if lang == "fr" else FALLBACK_EN
    return {
        "final_answer": template.format(error=last_error),
        "trace_steps": [
            step(
                "fallback",
                "max_retries_exhausted",
                last_error=str(last_error),
                last_cypher_draft=(state.get("cypher_draft") or "").strip(),
            )
        ],
    }