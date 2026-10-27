"""Execute read Cypher with row limits and basic serialization (agent-facing)."""
from __future__ import annotations

from typing import Any

from neo4j import Query

from config.settings import get_settings
from graph.client import get_driver

MAX_ROWS = 500


def _relationship_type(value: Any) -> str:
    rel_type = getattr(value, "type", "")
    if callable(rel_type):
        try:
            return str(rel_type())
        except Exception:
            return value.__class__.__name__
    if rel_type:
        return str(rel_type)
    return value.__class__.__name__


def _node_identifier(value: Any) -> str:
    element_id = getattr(value, "element_id", None)
    if element_id is not None:
        return str(element_id)
    node_id = getattr(value, "id", None)
    if node_id is not None:
        return str(node_id)
    return str(id(value))


def _relationship_endpoint(value: Any, attr_name: str) -> str:
    endpoint = getattr(value, attr_name, None)
    if endpoint is not None:
        try:
            return _node_identifier(endpoint)
        except Exception:
            return str(endpoint)
    alt_name = f"{attr_name}_id"
    alt_value = getattr(value, alt_name, None)
    if alt_value is not None:
        return str(alt_value)
    return ""


def _serialize_value(value: Any) -> Any:
    """Make Neo4j driver values JSON-safe (nested DateTime, Duration, etc.)."""
    if value is None:
        return None
    class_name = value.__class__.__name__ if hasattr(value, "__class__") else ""
    if class_name == "Node":
        return {
            "__kind": "node",
            "element_id": _node_identifier(value),
            "labels": [str(label) for label in list(getattr(value, "labels", []))],
            "properties": {
                k: _serialize_value(v) for k, v in dict(value).items()
            },
        }
    if class_name == "Relationship":
        return {
            "__kind": "relationship",
            "element_id": _node_identifier(value),
            "relationship_type": _relationship_type(value),
            "start_node_element_id": _relationship_endpoint(value, "start_node"),
            "end_node_element_id": _relationship_endpoint(value, "end_node"),
            "properties": {
                k: _serialize_value(v) for k, v in dict(value).items()
            },
        }
    if class_name == "Path":
        nodes = list(getattr(value, "nodes", []) or [])
        relationships = list(getattr(value, "relationships", []) or [])
        return {
            "__kind": "path",
            "nodes": [_serialize_value(node) for node in nodes],
            "relationships": [_serialize_value(rel) for rel in relationships],
        }
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialize_value(v) for k, v in record.items()}


def run_read_query(cypher: str) -> tuple[list[dict[str, Any]], str | None]:
    """
    Returns (records, error_message). error_message set on driver/query failure.
    """
    settings = get_settings()
    if getattr(settings, "DEMO_MODE", False):
        return [], None
    if getattr(settings, "mcp_enabled", lambda: False)():
        try:
            from graph.mcp_client import read_cypher

            return read_cypher(cypher)[:MAX_ROWS], None
        except Exception as e:
            return [], str(e)

    driver = get_driver()
    try:
        with driver.session() as session:
            raw = session.run(Query(cypher))
            records = [_serialize_record(dict(r)) for r in raw][:MAX_ROWS]
        return records, None
    except Exception as e:
        return [], str(e)
