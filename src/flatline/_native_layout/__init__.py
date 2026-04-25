"""Internal native graph layout bindings."""

from __future__ import annotations

import importlib
import sys

ogdf = importlib.import_module("flatline._flatline_native._native_layout.ogdf")

sys.modules[__name__ + ".ogdf"] = ogdf

__all__ = ["ogdf"]
