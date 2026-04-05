from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest

from flatline.xray import _inspector

from ._xray_support import make_sample_result

pytestmark = pytest.mark.unit


def test_inspector_formats_summary_and_node_details() -> None:
    result = make_sample_result()
    enriched = result.enriched
    assert enriched is not None
    pcode = enriched.pcode
    assert pcode is not None
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    summary_text = cast(Callable[..., str], _inspector.summary_text)
    op_text = cast(Callable[..., str], _inspector.op_text)
    varnode_text = cast(Callable[..., str], _inspector.varnode_text)

    assert _inspector.result_address(result.function_info, None) == "0x1000"
    assert _inspector.result_address(None, 0x4000) == "0x4000"
    assert _inspector.result_address(None, None) == "unknown"

    summary = summary_text(
        "Flatline X-Ray",
        result=result,
        pcode=pcode,
        target_label="x86:LE:64:default / gcc",
        source_label="fx_add_elf64.hex",
        fallback_address=0x1000,
    )
    assert "Input:     fx_add_elf64.hex" in summary
    assert "Target:    x86:LE:64:default / gcc" in summary
    assert "Function:  add" in summary
    assert "Warnings:" in summary
    assert "analyze: analyze.W001 | synthetic warning" in summary

    op_text_result = op_text(pcode.pcode_ops[0], varnode_by_id, depth=1)
    assert "Opcode:       INT_ADD" in op_text_result
    assert "Inputs:" in op_text_result
    assert "v0: INPUT register@0x0 size=4" in op_text_result
    assert "Output:" in op_text_result
    assert "v2: TEMP unique@0x100 size=4" in op_text_result

    varnode_text_result = varnode_text(varnode_by_id[2], op_by_id, depth=2)
    assert "Varnode v2" in varnode_text_result
    assert "Badge:        TEMP" in varnode_text_result
    assert "Defined by:" in varnode_text_result
    assert "op#0: INT_ADD" in varnode_text_result
    assert "Used by:" in varnode_text_result

    assert _inspector.varnode_brief(varnode_by_id[3]) == "CONST ram@0x200 size=8"
