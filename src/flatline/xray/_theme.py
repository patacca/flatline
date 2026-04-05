from __future__ import annotations

STATE_NORMAL = "normal"
STATE_SELECTED = "selected"
STATE_RELATED = "related"
STATE_MUTED = "muted"
STATE_WARNING = "warning"
STATE_PANEL_SURFACE = "panel_surface"

BACKGROUND = "#07111c"
CANVAS_BG = "#08131f"
PANEL_BG = "#0d1726"
PANEL_SURFACE = PANEL_BG
CHROME = BACKGROUND

TEXT = "#eef6ff"
TEXT_MUTED = "#93a7c1"
TEXT_WARNING = "#ffd166"
TEXT_ON_NODE = BACKGROUND

NODE_SHADOW = "#040a12"
NODE_OUTLINE = "#f8fbff"
NODE_OUTLINE_ALT = "#f4fff8"
NODE_OPCODE_DEFAULT = "#8ecae6"
NODE_OPCODE_WARNING = "#ff9f68"
NODE_OPCODE_MEMORY = "#f28482"
NODE_OPCODE_FLOW = "#ffd166"
NODE_OPCODE_CALL = "#ff6b6b"
NODE_VARNODE_DEFAULT = "#98f5e1"
NODE_VARNODE_INPUT = "#72ddf7"
NODE_VARNODE_PERSIST = "#95d5b2"
NODE_VARNODE_READ_ONLY = "#caffbf"
NODE_VARNODE_CONSTANT = "#ffd166"

EDGE_INPUT = "#54c6eb"
EDGE_OUTPUT = "#ff7b72"
EDGE_RELATED = "#a07cdc"

SELECTION_BACKGROUND = "#1e3a5f"
SELECTION_OUTLINE = "#ffb703"
SELECTION_TEXT = SELECTION_OUTLINE

DEPTH_BAND_OP_FILL = "#122235"
DEPTH_BAND_INPUT_FILL = "#0d2030"
DEPTH_BAND_OP_OUTLINE = "#1a3551"
DEPTH_BAND_INPUT_OUTLINE = "#102739"
# Muted label color for depth band row labels — less prominent than active text.
DEPTH_BAND_COLOR = "#0f1f30"

# Inactive (unselected, unrelated) edge visual tokens.
# Thinner and darker so active edges dominate when a node is selected.
EDGE_INACTIVE_COLOR = "#2a5a7a"
EDGE_INACTIVE_WIDTH = 1.0

TITLE_FONT = ("Helvetica", 24, "bold")
SUBTITLE_FONT = ("Helvetica", 11)
PANEL_TITLE_FONT = ("Helvetica", 14, "bold")
BODY_FONT = ("Courier", 10)
NODE_FONT = ("Helvetica", 10, "bold")
VARNODE_FONT = ("Helvetica", 9, "bold")
BAND_FONT = ("Helvetica", 10, "bold")

OPCODE_COLORS = {
    STATE_NORMAL: NODE_OPCODE_DEFAULT,
    STATE_WARNING: NODE_OPCODE_WARNING,
    STATE_RELATED: NODE_OPCODE_MEMORY,
    STATE_MUTED: NODE_OPCODE_FLOW,
    STATE_SELECTED: NODE_OPCODE_CALL,
}

VARNODE_COLORS = {
    STATE_NORMAL: NODE_VARNODE_DEFAULT,
    STATE_SELECTED: NODE_VARNODE_INPUT,
    STATE_RELATED: NODE_VARNODE_PERSIST,
    STATE_MUTED: NODE_VARNODE_READ_ONLY,
    STATE_WARNING: NODE_VARNODE_CONSTANT,
}


def opcode_color_for(opcode: str) -> str:
    if opcode.startswith(("INT_", "BOOL_", "FLOAT_")):
        return NODE_OPCODE_WARNING
    if opcode.startswith(("LOAD", "STORE")):
        return NODE_OPCODE_MEMORY
    if opcode in {"BRANCH", "CBRANCH", "BRANCHIND"}:
        return NODE_OPCODE_FLOW
    if opcode in {"CALL", "CALLIND", "RETURN"}:
        return NODE_OPCODE_CALL
    return NODE_OPCODE_DEFAULT


def varnode_color_for(varnode) -> str:
    if varnode.flags.is_constant:
        return NODE_VARNODE_CONSTANT
    if varnode.flags.is_input:
        return NODE_VARNODE_INPUT
    if varnode.flags.is_persist or varnode.flags.is_addr_tied:
        return NODE_VARNODE_PERSIST
    if varnode.flags.is_read_only:
        return NODE_VARNODE_READ_ONLY
    return NODE_VARNODE_DEFAULT


__all__ = [
    "BACKGROUND",
    "BAND_FONT",
    "BODY_FONT",
    "CANVAS_BG",
    "CHROME",
    "DEPTH_BAND_COLOR",
    "DEPTH_BAND_INPUT_FILL",
    "DEPTH_BAND_INPUT_OUTLINE",
    "DEPTH_BAND_OP_FILL",
    "DEPTH_BAND_OP_OUTLINE",
    "EDGE_INACTIVE_COLOR",
    "EDGE_INACTIVE_WIDTH",
    "EDGE_INPUT",
    "EDGE_OUTPUT",
    "EDGE_RELATED",
    "NODE_FONT",
    "NODE_OPCODE_CALL",
    "NODE_OPCODE_DEFAULT",
    "NODE_OPCODE_FLOW",
    "NODE_OPCODE_MEMORY",
    "NODE_OPCODE_WARNING",
    "NODE_OUTLINE",
    "NODE_OUTLINE_ALT",
    "NODE_SHADOW",
    "NODE_VARNODE_CONSTANT",
    "NODE_VARNODE_DEFAULT",
    "NODE_VARNODE_INPUT",
    "NODE_VARNODE_PERSIST",
    "NODE_VARNODE_READ_ONLY",
    "OPCODE_COLORS",
    "PANEL_BG",
    "PANEL_SURFACE",
    "PANEL_TITLE_FONT",
    "SELECTION_BACKGROUND",
    "SELECTION_OUTLINE",
    "SELECTION_TEXT",
    "STATE_MUTED",
    "STATE_NORMAL",
    "STATE_PANEL_SURFACE",
    "STATE_RELATED",
    "STATE_SELECTED",
    "STATE_WARNING",
    "SUBTITLE_FONT",
    "TEXT",
    "TEXT_MUTED",
    "TEXT_ON_NODE",
    "TEXT_WARNING",
    "TITLE_FONT",
    "VARNODE_COLORS",
    "VARNODE_FONT",
    "opcode_color_for",
    "varnode_color_for",
]
