from __future__ import annotations

from agent.state import AgentState
from agent.nodes.synthesizer import run_genui as _run_genui


def run(state: AgentState) -> dict:
    result = _run_genui(state)
    out = {
        "final_answer": result.get("final_answer", state.get("final_answer", "")),
        "genui_blocks": result.get("genui_blocks", []),
        "trace_steps": result.get("trace_steps", []),
    }
    if "messages" in result:
        out["messages"] = result["messages"]
    return out
