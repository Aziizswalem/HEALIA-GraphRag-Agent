"""Small helpers for structured trace entries (LangGraph `trace_steps` reducer)."""


def step(node: str, event: str, **fields: object) -> dict:
    row: dict = {"node": node, "event": event}
    for k, v in fields.items():
        if v is not None:
            row[k] = v
    return row
