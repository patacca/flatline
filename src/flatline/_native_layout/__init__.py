"""Internal native graph layout bindings."""

from __future__ import annotations

import importlib
import sys

ogdf = importlib.import_module("flatline._flatline_native._native_layout.ogdf")
avoid = importlib.import_module("flatline._flatline_native._native_layout.avoid")

sys.modules[__name__ + ".ogdf"] = ogdf
sys.modules[__name__ + ".avoid"] = avoid

__all__ = ["avoid", "ogdf"]
