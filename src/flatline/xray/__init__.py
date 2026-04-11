"""flatline.xray alpha package.

The flatline.xray API is alpha and may change between minor releases without
deprecation notice.
"""

from __future__ import annotations

__all__ = ["XrayWindow", "main"]


def main(argv: list[str] | None = None, *, cpg: bool = False) -> int:
    """Run the X-Ray CLI entry point without importing tkinter eagerly."""
    from flatline.xray.__main__ import main as _main

    return _main(argv)


def __getattr__(name: str):
    if name == "XrayWindow":
        from flatline.xray._graph_window import XrayWindow

        return XrayWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
