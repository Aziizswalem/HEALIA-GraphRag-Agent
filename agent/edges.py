from agent.state import AgentState

MAX_RETRIES = 3


def after_validation(state: AgentState) -> str:
    """
    Called after the validator node.
    Returns the name of the next node to visit.
    """
    has_error = bool(state.get("validation_error"))
    retry_count = state.get("retry_count", 0)

    if not has_error:
        return "execute"           # Valid Cypher → run it

    if retry_count < MAX_RETRIES:
        return "retry"             # Still have retries → back to generator

    return "fallback"              # Exhausted retries → give up gracefully


def after_execution(state: AgentState) -> str:
    """
    Called after the executor node.
    If executor set final_answer directly (on error), skip synthesizer.
    """
    if state.get("final_answer"):
        return "done"
    return "synthesize"