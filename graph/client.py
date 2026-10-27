"""Singleton Neo4j driver for read-heavy agent workloads."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)

_driver: Driver | None = None


class _MockDriver:
    """Mock Neo4j driver for DEMO_MODE or offline environments."""

    def close(self) -> None:
        pass

    def verify_connectivity(self) -> None:
        pass

    def session(self, **kwargs: Any) -> Any:
        raise RuntimeError("Neo4j is offline or DEMO_MODE is active.")


def get_driver() -> "Driver":
    global _driver
    if _driver is not None:
        return _driver

    from config.settings import get_settings

    s = get_settings()

    if getattr(s, "DEMO_MODE", False):
        logger.info("DEMO_MODE is active: bypassing Neo4j Bolt connection.")
        _driver = _MockDriver()  # type: ignore[assignment]
        return _driver

    try:
        from neo4j import GraphDatabase

        _driver = GraphDatabase.driver(
            s.NEO4J_URI,
            auth=(s.neo4j_auth_user(), s.NEO4J_PASSWORD),
        )
        return _driver
    except Exception as exc:
        logger.warning(
            "Could not connect to Neo4j Bolt instance (%s). Falling back to mock driver.",
            exc,
        )
        _driver = _MockDriver()  # type: ignore[assignment]
        return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        try:
            _driver.close()
        except Exception:
            pass
        _driver = None
