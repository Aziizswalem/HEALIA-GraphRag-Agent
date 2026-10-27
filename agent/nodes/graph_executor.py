from agent.state import AgentState
from agent.trace_util import step
from config.settings import get_settings
from graph.executor import run_read_query


def run(state: AgentState) -> dict:
    s = get_settings()
    graph_access_configured = getattr(
        s,
        "graph_access_configured",
        lambda: bool(s.neo4j_auth_user()),
    )
    if not graph_access_configured():
        return {
            "graph_results": [],
            "final_answer": "Configuration error: set MCP_URL or NEO4J_USER/NEO4J_USERNAME.",
            "trace_steps": [
                step(
                    "graph_executor",
                    "execution_skipped",
                    reason="config",
                )
            ],
        }

    records, err = run_read_query(state["cypher_draft"])
    if err:
        return {
            "graph_results": [],
            "final_answer": f"Erreur lors de l'exécution de la requête : {err}",
            "trace_steps": [
                step(
                    "graph_executor",
                    "execution_failed",
                    neo4j_executed=True,
                    error=str(err),
                    cypher=state.get("cypher_draft") or "",
                )
            ],
        }
    out = [dict(record) for record in (records or [])]
    sample_rows = out[:3]
    sample_keys = sorted({key for row in sample_rows for key in row.keys()})
    return {
        "graph_results": out,
        "trace_steps": [
            step(
                "graph_executor",
                "execution_ok",
                neo4j_executed=True,
                row_count=len(out),
                sample_keys=sample_keys,
                sample_rows=sample_rows,
            )
        ],
    }
