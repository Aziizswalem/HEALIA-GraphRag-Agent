"""AG-UI / CopilotKit endpoint — exposes the compiled LangGraph agent."""
from __future__ import annotations

from fastapi import FastAPI

from agent.graph import agent as compiled_agent
from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint


def register_copilotkit(app: FastAPI, path: str = "/copilotkit") -> None:
    """Create and register the AG-UI LangGraphAgent on the FastAPI app."""

    @app.get(f"{path}/info")
    @app.post(f"{path}/info")
    def copilotkit_info():
        return {
            "version": "1.64.1",
            "agents": {
                "graphrag_agent": {
                    "name": "graphrag_agent",
                    "description": "Health insurance GraphRAG assistant — queries Neo4j and returns GenUI blocks.",
                    "capabilities": {},
                }
            },
        }

    agent = LangGraphAgent(
        name="graphrag_agent",
        graph=compiled_agent,
        description="Health insurance GraphRAG assistant — queries Neo4j and returns GenUI blocks.",
    )
    add_langgraph_fastapi_endpoint(app, agent=agent, path=path)
