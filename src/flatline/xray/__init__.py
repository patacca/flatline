"""flatline.xray alpha package.

The flatline.xray API is alpha and may change between minor releases without
deprecation notice.
"""

from __future__ import annotations

from flatline.xray.__main__ import main

__all__ = ["XrayWindow", "main"]


def __getattr__(name: str):
    if name == "XrayWindow":
        from flatline.xray._graph_window import XrayWindow

        return XrayWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
