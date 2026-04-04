"""Text-formatting helpers for flatline.xray."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flatline.models import FunctionInfo, PcodeOpInfo, VarnodeInfo


def result_address(info: "FunctionInfo | None", fallback_address: int | None = None) -> str:
    """Return the best available function address."""

    if info is not None:
        return f"0x{info.entry_address:x}"
    if fallback_address is not None:
        return f"0x{fallback_address:x}"
    return "unknown"


def summary_text(
    window_title: str,
    *,
    result,
    pcode,
    target_label: str,
    source_label: str | None = None,
    fallback_address: int | None = None,
) -> str:
    """Render the summary panel text."""

    info = result.function_info
    c_block = textwrap.fill(result.c_code or "<no C output>", width=42)
    warning_lines = (
        "\n".join(
            f"  - {warning.phase}: {warning.code} | {warning.message}"
            for warning in result.warnings
        )
        if result.warnings
        else "  - none"
    )
    lines = [window_title, ""]
    if source_label is not None:
        lines.append(f"Input:     {source_label}")
    lines.extend(
        [
            f"Target:    {target_label}",
            f"Function:  {info.name if info is not None else 'unknown'}",
            f"Address:   {result_address(info, fallback_address)}",
            f"Size:      {info.size if info is not None else '?'} bytes",
            f"Ops:       {len(pcode.pcode_ops)}",
            f"Varnodes:  {len(pcode.varnodes)}",
        ]
    )
    lines.extend(
        [
            "",
            "Recovered C:",
            c_block,
            "",
            "Legend:",
            "  - squares: pcode ops",
            "  - circles: varnodes",
            "  - triangles: constants",
            "  - blue: inputs flowing into ops",
            "  - coral: outputs produced by ops",
            "",
            "Warnings:",
            warning_lines,
            "",
            "Click a node to inspect addresses, flags, and use-def links.",
        ]
    )
    return "\n".join(lines)


def op_text(
    op: "PcodeOpInfo",
    varnode_by_id,
    *,
    depth: int,
) -> str:
    """Render the inspector text for one pcode op."""

    input_lines = [
        f"  - v{varnode_id}: {varnode_brief(varnode_by_id[varnode_id])}"
        for varnode_id in op.input_varnode_ids
        if varnode_id in varnode_by_id
    ]
    output_line = (
        f"  - v{op.output_varnode_id}: {varnode_brief(varnode_by_id[op.output_varnode_id])}"
        if op.output_varnode_id in varnode_by_id
        else "  - none"
    )
    return "\n".join(
        [
            f"P-code op #{op.id}",
            "",
            f"Opcode:       {op.opcode}",
            f"Tree depth:   {depth}",
            f"Insn addr:    0x{op.instruction_address:x}",
            f"Seq time:     {op.sequence_time}",
            f"Seq order:    {op.sequence_order}",
            "",
            "Inputs:",
            "\n".join(input_lines) if input_lines else "  - none",
            "",
            "Output:",
            output_line,
        ]
    )


def varnode_text(
    varnode: "VarnodeInfo",
    op_by_id,
    *,
    depth: int,
) -> str:
    """Render the inspector text for one varnode."""

    flag_lines = [
        name.replace("is_", "")
        for name in (
            "is_constant",
            "is_input",
            "is_free",
            "is_implied",
            "is_explicit",
            "is_read_only",
            "is_persist",
            "is_addr_tied",
        )
        if getattr(varnode.flags, name)
    ]
    badge = _badge_for_varnode(varnode)
    use_lines = [
        f"  - op#{op_id}: {op_by_id[op_id].opcode}"
        for op_id in varnode.use_op_ids
        if op_id in op_by_id
    ]
    defining_line = (
        f"  - op#{varnode.defining_op_id}: {op_by_id[varnode.defining_op_id].opcode}"
        if varnode.defining_op_id in op_by_id
        else "  - none"
    )
    return "\n".join(
        [
            f"Varnode v{varnode.id}",
            "",
            f"Badge:        {badge}",
            f"Tree depth:   {depth}",
            f"Space:        {varnode.space}",
            f"Offset:       0x{varnode.offset:x}",
            f"Size:         {varnode.size} bytes",
            "",
            "Flags:",
            f"  - {', '.join(flag_lines) if flag_lines else 'none'}",
            "",
            "Defined by:",
            defining_line,
            "",
            "Used by:",
            "\n".join(use_lines) if use_lines else "  - none",
        ]
    )


def varnode_brief(varnode: "VarnodeInfo") -> str:
    """Render a compact one-line description of a varnode."""

    badge = _badge_for_varnode(varnode)
    return f"{badge} {varnode.space}@0x{varnode.offset:x} size={varnode.size}"


def _badge_for_varnode(varnode: "VarnodeInfo") -> str:
    if varnode.flags.is_constant:
        return "CONST"
    if varnode.flags.is_input:
        return "INPUT"
    if varnode.space == "register":
        return "REG"
    if varnode.space == "ram":
        return "RAM"
    if varnode.space == "unique":
        return "TEMP"
    return varnode.space[:6].upper()


__all__ = [
    "op_text",
    "result_address",
    "summary_text",
    "varnode_brief",
    "varnode_text",
]
