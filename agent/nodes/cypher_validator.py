"""Compatibility alias for the improved Cypher validator."""

from __future__ import annotations

import sys

from agent.nodes import cypher_validator_updated as _updated

sys.modules[__name__] = _updated
