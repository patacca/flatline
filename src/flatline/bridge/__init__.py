"""Bridge package for the internal Python/native adapter layer."""

from __future__ import annotations

from flatline.bridge.core import BridgeSession, create_bridge_session

__all__ = [
    "BridgeSession",
    "create_bridge_session",
]
