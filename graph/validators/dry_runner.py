"""Neo4j EXPLAIN dry-run: compile query plan without reading data."""
from __future__ import annotations

from neo4j import Query
from neo4j.exceptions import ClientError, CypherSyntaxError

from config.settings import get_settings
from graph.client import get_driver


def explain_cypher(cypher: str) -> str | None:
    """Return None if EXPLAIN succeeds, else Neo4j error string."""
    settings = get_settings()
    if getattr(settings, "DEMO_MODE", False):
        return None
    if getattr(settings, "mcp_enabled", lambda: False)():
        try:
            from graph.mcp_client import read_cypher

            read_cypher(f"EXPLAIN {cypher}")
            return None
        except Exception as e:
            return str(e)

    driver = get_driver()
    try:
        with driver.session() as session:
            session.run(Query(f"EXPLAIN {cypher}")).consume()
        return None
    except (CypherSyntaxError, ClientError) as e:
        return str(e)
