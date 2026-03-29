"""Unit tests for public Python contract (specs.md section 3).

Tests validate data model construction, field enforcement, error taxonomy,
and advisory-field passthrough -- all pure Python, no native bridge required.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from flatline import (
    AnalysisBudget,
    DecompileRequest,
    FlatlineError,
    InvalidArgumentError,
    Pcode,
    PcodeOpInfo,
    UnsupportedTargetError,
    VarnodeFlags,
    VarnodeInfo,
)
from flatline._models import _validate_compiler_spec

# ---------------------------------------------------------------------------
# U-001: Request schema rejects missing required fields
# ---------------------------------------------------------------------------


def test_u001_request_schema_required_fields():
    """U-001: Missing required request fields map to structured invalid_argument errors."""
    base_kwargs: dict[str, object] = {
        "memory_image": b"\xcc",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
    }

    # Each required field omitted -> TypeError (Python enforcement)
    for field in ("memory_image", "base_address", "function_address", "language_id"):
        kwargs = {k: v for k, v in base_kwargs.items() if k != field}
        with pytest.raises(TypeError):
            DecompileRequest(**kwargs)

    # Empty memory image -> InvalidArgumentError (semantic validation, specs.md section 3.4)
    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**{**base_kwargs, "memory_image": b""})
    assert exc_info.value.category == "invalid_argument"

    # Empty language_id -> InvalidArgumentError
    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**{**base_kwargs, "language_id": ""})
    assert exc_info.value.category == "invalid_argument"

    # Valid construction succeeds
    req = DecompileRequest(**base_kwargs)
    assert req.memory_image == b"\xcc"
    assert req.base_address == 0x1000
    assert req.function_address == 0x1000
    assert req.language_id == "x86:LE:64:default"

    # Optional fields default to None
    assert req.compiler_spec is None
    assert req.runtime_data_dir is None
    assert req.function_size_hint is None
    assert req.analysis_budget == AnalysisBudget()
    assert req.enriched is False
    assert req.tail_padding == b"\x00"


# ---------------------------------------------------------------------------
# U-002: Unknown compiler id handling
# ---------------------------------------------------------------------------


def test_u002_unknown_compiler_rejected_without_fallback():
    """U-002: Unknown compiler identifiers are hard failures, never implicit fallback."""
    known_specs = frozenset({"gcc", "default", "windows"})

    # Unknown compiler -> UnsupportedTargetError
    with pytest.raises(UnsupportedTargetError) as exc_info:
        _validate_compiler_spec("unknown_compiler", known_specs)
    assert exc_info.value.category == "unsupported_target"

    # Empty string -> UnsupportedTargetError (no empty-string fallback)
    with pytest.raises(UnsupportedTargetError):
        _validate_compiler_spec("", known_specs)

    # Known compiler passes without error
    _validate_compiler_spec("gcc", known_specs)
    _validate_compiler_spec("default", known_specs)

    # Error inherits from FlatlineError
    assert issubclass(UnsupportedTargetError, FlatlineError)


def test_request_accepts_pathlike_runtime_data_dir() -> None:
    """Runtime-data overrides accept `Path` inputs from `ghidra_sleigh`."""
    runtime_dir = Path("/tmp/flatline-runtime")
    request = DecompileRequest(
        memory_image=b"\xcc\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        runtime_data_dir=runtime_dir,
    )

    assert request.runtime_data_dir == str(runtime_dir)


def test_request_tail_padding_defaults_and_validates() -> None:
    """U-031: Tail padding defaults on and normalizes disable/custom values."""
    base_kwargs: dict[str, object] = {
        "memory_image": b"\xcc\xc3",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
    }

    default_request = DecompileRequest(**base_kwargs)
    assert default_request.tail_padding == b"\x00"

    custom_request = DecompileRequest(**base_kwargs, tail_padding=b"\x90\x91")
    assert custom_request.tail_padding == b"\x90\x91"

    bytearray_request = DecompileRequest(**base_kwargs, tail_padding=bytearray(b"\xaa"))
    assert bytearray_request.tail_padding == b"\xaa"

    disabled_request = DecompileRequest(**base_kwargs, tail_padding=None)
    assert disabled_request.tail_padding is None

    empty_padding_request = DecompileRequest(**base_kwargs, tail_padding=b"")
    assert empty_padding_request.tail_padding is None

    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**base_kwargs, tail_padding="no")
    assert exc_info.value.category == "invalid_argument"


# ---------------------------------------------------------------------------
# U-006: analysis_budget defaults and validation
# ---------------------------------------------------------------------------


def test_u006_analysis_budget_passthrough():
    """U-006: analysis_budget defaults deterministically and coerces supported inputs."""
    base_kwargs: dict[str, object] = {
        "memory_image": b"\xcc\xc3",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
    }

    # Without budget -- defaults to the pinned instruction cap
    req_no_budget = DecompileRequest(**base_kwargs)
    assert req_no_budget.analysis_budget == AnalysisBudget(max_instructions=100000)

    # With budget object -- value preserved
    budget = AnalysisBudget(max_instructions=50000)
    req_with_budget = DecompileRequest(**base_kwargs, analysis_budget=budget)
    assert req_with_budget.analysis_budget == budget

    # With budget mapping -- value coerced to AnalysisBudget
    req_with_mapping = DecompileRequest(
        **base_kwargs,
        analysis_budget={"max_instructions": 4096},
    )
    assert req_with_mapping.analysis_budget == AnalysisBudget(max_instructions=4096)

    # Empty mapping still resolves to the default budget
    req_with_empty_mapping = DecompileRequest(**base_kwargs, analysis_budget={})
    assert req_with_empty_mapping.analysis_budget == AnalysisBudget()


def test_u006_analysis_budget_rejects_unsupported_fields_and_values():
    """U-006: analysis_budget rejects unsupported keys and invalid instruction limits."""
    base_kwargs: dict[str, object] = {
        "memory_image": b"\xcc\xc3",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
    }

    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**base_kwargs, analysis_budget={"timeout_ms": 5000})
    assert exc_info.value.category == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**base_kwargs, analysis_budget={"max_instructions": 0})
    assert exc_info.value.category == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**base_kwargs, analysis_budget={"max_instructions": True})
    assert exc_info.value.category == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**base_kwargs, analysis_budget=object())
    assert exc_info.value.category == "invalid_argument"


def _build_pcode_fixture() -> Pcode:
    return Pcode(
        pcode_ops=[
            PcodeOpInfo(
                id=10,
                opcode="INT_ADD",
                instruction_address=0x1000,
                sequence_time=0,
                sequence_order=0,
                input_varnode_ids=[1, 1],
                output_varnode_id=3,
            ),
            PcodeOpInfo(
                id=11,
                opcode="RETURN",
                instruction_address=0x1001,
                sequence_time=1,
                sequence_order=0,
                input_varnode_ids=[3],
                output_varnode_id=None,
            ),
        ],
        varnodes=[
            VarnodeInfo(
                id=1,
                space="register",
                offset=0,
                size=4,
                flags=VarnodeFlags(False, True, False, False, True, False, False, False),
                defining_op_id=None,
                use_op_ids=[10],
            ),
            VarnodeInfo(
                id=3,
                space="unique",
                offset=0x100,
                size=4,
                flags=VarnodeFlags(False, False, False, False, True, False, False, False),
                defining_op_id=10,
                use_op_ids=[11],
            ),
        ],
    )


def test_u029_pcode_lookup_and_graph_projection_are_deterministic() -> None:
    """U-029: Pcode exposes id lookup and a deterministic multigraph projection."""
    pcode = _build_pcode_fixture()

    assert pcode.get_pcode_op(10).opcode == "INT_ADD"
    assert pcode.get_varnode(3).defining_op_id == 10

    graph = pcode.to_graph()
    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.nodes[("op", 10)]["kind"] == "pcode_op"
    assert graph.nodes[("op", 10)]["op"] == pcode.get_pcode_op(10)
    assert graph.nodes[("varnode", 3)]["kind"] == "varnode"
    assert graph.nodes[("varnode", 3)]["varnode"] == pcode.get_varnode(3)

    duplicate_input_edges = graph.get_edge_data(("varnode", 1), ("op", 10))
    assert duplicate_input_edges is not None
    assert len(duplicate_input_edges) == 2
    assert sorted(edge["input_index"] for edge in duplicate_input_edges.values()) == [0, 1]
    assert all(edge["kind"] == "input" for edge in duplicate_input_edges.values())

    output_edges = graph.get_edge_data(("op", 10), ("varnode", 3))
    assert output_edges is not None
    assert len(output_edges) == 1
    assert next(iter(output_edges.values()))["kind"] == "output"


def test_u029_pcode_lookup_rejects_invalid_ids() -> None:
    """U-029: Pcode id lookup fails hard on malformed or missing ids."""
    pcode = _build_pcode_fixture()

    with pytest.raises(InvalidArgumentError) as exc_info:
        pcode.get_pcode_op("bad")  # type: ignore[arg-type]
    assert exc_info.value.category == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as exc_info:
        pcode.get_pcode_op(999)
    assert exc_info.value.category == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as exc_info:
        pcode.get_varnode(True)  # type: ignore[arg-type]
    assert exc_info.value.category == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as exc_info:
        pcode.get_varnode(999)
    assert exc_info.value.category == "invalid_argument"
