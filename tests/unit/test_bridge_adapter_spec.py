"""Unit tests for bridge adapter behavior (specs.md section 3.2, section 6)."""

from __future__ import annotations

import pytest

from flatline import (
    AnalysisBudget,
    DecompileRequest,
    DecompileResult,
    Enriched,
    FunctionInfo,
    InstructionInfo,
    LanguageCompilerPair,
    Pcode,
    PcodeOpInfo,
    VarnodeFlags,
    VarnodeInfo,
)
from flatline._errors import InternalError
from flatline.bridge import core as bridge_module
from flatline.bridge.payloads import (
    _coerce_enriched,
    _coerce_instruction_info,
    _coerce_pcode_op,
    _coerce_varnode_info,
)
from flatline.models.enums import PcodeOpcode, VarnodeSpace
from flatline.models.pcode_ops import (
    Cast,
    Cbranch,
    Indirect,
    IntAdd,
    Multiequal,
    Ptradd,
    Ptrsub,
)
from flatline.models.varnodes import FspecVarnode, IopVarnode, RegisterVarnode

from ._bridge_doubles import (
    _NativeModuleDouble,
    _NativeSessionMissingEnrichedDouble,
    _NativeSessionMissingPcodeDouble,
    _NativeSessionSuccessDouble,
)

_TEST_VARNODE_FLAGS = {
    "is_constant": False,
    "is_input": True,
    "is_free": False,
    "is_implied": False,
    "is_explicit": True,
    "is_read_only": False,
    "is_persist": False,
    "is_addr_tied": False,
}


def _make_varnode_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 0,
        "space": "register",
        "offset": 0,
        "size": 4,
        "flags": dict(_TEST_VARNODE_FLAGS),
        "defining_op_id": None,
        "use_op_ids": [],
        "call_site_index": None,
        "target_op_id": None,
    }
    payload.update(overrides)
    return payload


def _make_request(**overrides: object) -> DecompileRequest:
    payload: dict[str, object] = {
        "memory_image": b"\x90\xc3",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
        "compiler_spec": "gcc",
    }
    payload.update(overrides)
    return DecompileRequest(**payload)


def test_u010_bridge_session_fallback_when_native_module_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-010: Missing native extension falls back to deterministic Python bridge."""

    def _raise_import_error(_: str) -> object:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))
    assert isinstance(bridge_session, bridge_module._FallbackBridgeSession)


def test_u011_bridge_session_adapts_native_payloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-011: Native tuple/dict payloads are adapted to public model types."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)

    monkeypatch.setattr(
        bridge_module.importlib,
        "import_module",
        lambda _: native_module,
    )

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))
    assert native_module.runtime_data_dir == str(runtime_dir)

    pairs = bridge_session.list_language_compilers()
    assert pairs == [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]

    request = _make_request()
    result = bridge_session.decompile_function(request)

    assert isinstance(result, DecompileResult)
    assert result.error is None
    assert isinstance(result.function_info, FunctionInfo)
    assert result.metadata["language_id"] == "x86:LE:64:default"
    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["memory_image"] == b"\x90\xc3"
    assert native_session.last_request_payload["base_address"] == 0x1000
    assert native_session.last_request_payload["function_address"] == 0x1000
    assert native_session.last_request_payload["analysis_budget"] == {
        "max_instructions": 100000,
    }
    assert native_session.last_request_payload["tail_padding"] == b"\x00"

    bridge_session.close()
    assert native_session.closed is True


def test_u011_bridge_serializes_explicit_analysis_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-011: Explicit analysis budgets use the stable native payload shape."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    request = _make_request(analysis_budget=AnalysisBudget(max_instructions=4096))
    bridge_session.decompile_function(request)

    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["analysis_budget"] == {
        "max_instructions": 4096,
    }


def test_u011_bridge_serializes_explicit_tail_padding_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-011: Tail padding uses the stable native payload shape."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    request = _make_request(tail_padding=b"\x1f\x20\x03\xd5")
    bridge_session.decompile_function(request)

    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["tail_padding"] == b"\x1f\x20\x03\xd5"

    disabled_request = _make_request(tail_padding=b"")
    bridge_session.decompile_function(disabled_request)

    assert native_session.last_request_payload["tail_padding"] is None


def test_u028_bridge_session_adapts_enriched_payload_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-028: Native enriched-output payloads adapt to public frozen model types."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    request = _make_request(enriched=True)
    result = bridge_session.decompile_function(request)

    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["enriched"] is True
    assert isinstance(result.enriched, Enriched)
    assert isinstance(result.enriched.pcode, Pcode)
    assert isinstance(result.enriched.pcode.pcode_ops[0], PcodeOpInfo)
    assert isinstance(result.enriched.pcode.varnodes[0], VarnodeInfo)
    assert isinstance(result.enriched.pcode.varnodes[0].flags, VarnodeFlags)
    assert result.enriched.pcode.pcode_ops[0].opcode == "INT_ADD"
    assert result.enriched.pcode.get_varnode(2).use_op_ids == [3]
    assert result.enriched.pcode.get_varnode(3).call_site_index == 0
    assert result.enriched.pcode.get_varnode(3).offset == 0
    assert result.enriched.pcode.get_varnode(5).target_op_id == 2
    assert result.enriched.pcode.get_varnode(5).offset == 0
    assert result.function_info is not None
    assert result.function_info.call_sites[0].instruction_address == request.function_address + 3


def test_u040_bridge_populates_enriched_instructions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    request = _make_request(enriched=True)
    result = bridge_session.decompile_function(request)

    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["enriched"] is True
    assert result.enriched is not None
    assert result.enriched.instructions is not None
    assert result.enriched.instructions[0] == InstructionInfo(
        address=0x1000,
        length=3,
        mnemonic="ADD",
        operands="EAX, EBX",
    )


def test_u028_bridge_rejects_missing_enriched_payload_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-028: Opt-in enriched output must not silently disappear on success."""
    native_module = _NativeModuleDouble(native_session=_NativeSessionMissingEnrichedDouble())
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session()
    request = _make_request(enriched=True)

    result = bridge_session.decompile_function(request)

    assert result.error is not None
    assert result.error.category == "internal_error"
    assert result.enriched is None


def test_u028_bridge_rejects_missing_pcode_when_enriched_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-028: Enriched present but pcode missing must not silently pass."""
    native_module = _NativeModuleDouble(native_session=_NativeSessionMissingPcodeDouble())
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session()
    request = _make_request(enriched=True)

    result = bridge_session.decompile_function(request)

    assert result.error is not None
    assert result.error.category == "internal_error"
    assert result.enriched is None


def test_u029_bridge_coerces_instruction_payloads() -> None:
    instruction = _coerce_instruction_info(
        {
            "address": 4096,
            "length": 3,
            "mnemonic": "MOV",
            "operands": "eax, ebx",
        }
    )
    assert isinstance(instruction, InstructionInfo)
    assert instruction == InstructionInfo(
        address=4096,
        length=3,
        mnemonic="MOV",
        operands="eax, ebx",
    )

    passthrough = InstructionInfo(address=8192, length=4, mnemonic="ADD", operands="eax, ecx")
    assert _coerce_instruction_info(passthrough) is passthrough

    enriched = _coerce_enriched(
        {
            "pcode": None,
            "instructions": [
                {
                    "address": 4096,
                    "length": 3,
                    "mnemonic": "MOV",
                    "operands": "eax, ebx",
                }
            ],
        }
    )
    assert enriched is not None
    assert enriched.instructions is not None
    assert enriched.instructions[0] == instruction


def test_u029_bridge_coerces_cbranch_target_addresses() -> None:
    pcode_op = _coerce_pcode_op(
        {
            "id": 11,
            "opcode": "CBRANCH",
            "instruction_address": 0x401000,
            "sequence_time": 7,
            "sequence_order": 1,
            "input_varnode_ids": [5],
            "output_varnode_id": None,
            "true_target_address": 0x401020,
            "false_target_address": 0x401030,
        }
    )

    # Verify subclass type
    assert isinstance(pcode_op, Cbranch)
    # Verify opcode is enum
    assert isinstance(pcode_op.opcode, PcodeOpcode)
    assert pcode_op.opcode == PcodeOpcode.CBRANCH
    # Verify base fields
    assert pcode_op.id == 11
    assert pcode_op.instruction_address == 0x401000
    assert pcode_op.sequence_time == 7
    assert pcode_op.sequence_order == 1
    assert pcode_op.input_varnode_ids == [5]
    assert pcode_op.output_varnode_id is None
    assert pcode_op.true_target_address == 0x401020
    assert pcode_op.false_target_address == 0x401030


def test_u029_bridge_defaults_missing_pcode_target_addresses_to_none() -> None:
    pcode_op = _coerce_pcode_op(
        {
            "id": 12,
            "opcode": "INT_ADD",
            "instruction_address": 0x401040,
            "sequence_time": 8,
            "sequence_order": 2,
            "input_varnode_ids": [1, 2],
            "output_varnode_id": 3,
        }
    )

    # Verify subclass type
    assert isinstance(pcode_op, IntAdd)
    # Verify opcode is enum
    assert isinstance(pcode_op.opcode, PcodeOpcode)
    assert pcode_op.opcode == PcodeOpcode.INT_ADD
    # Verify target addresses default to None
    assert pcode_op.true_target_address is None
    assert pcode_op.false_target_address is None


def test_u029_bridge_accepts_explicit_none_pcode_target_addresses() -> None:
    pcode_op = _coerce_pcode_op(
        {
            "id": 13,
            "opcode": "CBRANCH",
            "instruction_address": 0x401060,
            "sequence_time": 9,
            "sequence_order": 3,
            "input_varnode_ids": [4],
            "output_varnode_id": None,
            "true_target_address": None,
            "false_target_address": None,
        }
    )

    # Verify subclass type
    assert isinstance(pcode_op, Cbranch)
    assert pcode_op.true_target_address is None
    assert pcode_op.false_target_address is None


def test_u029_bridge_coerces_varnode_call_site_index() -> None:
    varnode = _coerce_varnode_info(
        _make_varnode_payload(id=7, space="fspec", size=8, use_op_ids=[11], call_site_index=0)
    )

    # Verify subclass type
    assert isinstance(varnode, FspecVarnode)
    # Verify space is enum
    assert isinstance(varnode.space, VarnodeSpace)
    assert varnode.space == VarnodeSpace.FSPEC
    assert varnode.call_site_index == 0


def test_u029_bridge_defaults_missing_varnode_call_site_index_to_none() -> None:
    varnode = _coerce_varnode_info(_make_varnode_payload(id=8, offset=4))

    # Verify subclass type (default space is "register")
    assert isinstance(varnode, RegisterVarnode)
    assert varnode.call_site_index is None


def test_u029_bridge_coerces_explicit_none_varnode_call_site_index() -> None:
    varnode = _coerce_varnode_info(_make_varnode_payload(id=9, offset=8, call_site_index=None))

    # Verify subclass type (default space is "register")
    assert isinstance(varnode, RegisterVarnode)
    assert varnode.call_site_index is None


def test_u029_bridge_coerces_varnode_target_op_id_zero() -> None:
    varnode = _coerce_varnode_info(
        _make_varnode_payload(
            id=10,
            space="iop",
            size=8,
            flags={**_TEST_VARNODE_FLAGS, "is_input": False},
            target_op_id=0,
        )
    )

    # Verify subclass type
    assert isinstance(varnode, IopVarnode)
    # Verify space is enum
    assert isinstance(varnode.space, VarnodeSpace)
    assert varnode.space == VarnodeSpace.IOP
    assert varnode.target_op_id == 0


def test_u029_bridge_defaults_missing_varnode_target_op_id_to_none() -> None:
    varnode = _coerce_varnode_info(_make_varnode_payload(id=11, offset=4))

    # Verify subclass type (default space is "register")
    assert isinstance(varnode, RegisterVarnode)
    assert varnode.target_op_id is None


def test_u029_bridge_coerces_explicit_none_varnode_target_op_id() -> None:
    varnode = _coerce_varnode_info(
        _make_varnode_payload(
            id=12,
            space="iop",
            size=8,
            flags={**_TEST_VARNODE_FLAGS, "is_input": False},
            target_op_id=None,
        )
    )

    # Verify subclass type
    assert isinstance(varnode, IopVarnode)
    assert varnode.target_op_id is None


def test_u030_bridge_rejects_malformed_instruction_payloads() -> None:
    with pytest.raises(InternalError):
        _coerce_instruction_info(
            {
                "length": 3,
                "mnemonic": "MOV",
                "operands": "eax, ebx",
            }
        )

    enriched = _coerce_enriched({"pcode": None, "instructions": None})
    assert enriched is not None
    assert enriched.instructions is None


def test_u031_bridge_rejects_unknown_pcode_opcode() -> None:
    with pytest.raises(
        ValueError,
        match=r"Unknown pcode opcode 'UNKNOWN_OPCODE'. Update flatline.",
    ):
        _coerce_pcode_op(
            {
                "id": 1,
                "opcode": "UNKNOWN_OPCODE",
                "instruction_address": 0x401000,
                "sequence_time": 0,
                "sequence_order": 0,
                "input_varnode_ids": [],
                "output_varnode_id": None,
            }
        )


@pytest.mark.parametrize(
    ("raw_opcode", "canonical_opcode", "expected_type"),
    [
        ("BUILD", PcodeOpcode.MULTIEQUAL, Multiequal),
        ("DELAY_SLOT", PcodeOpcode.INDIRECT, Indirect),
        ("LABEL", PcodeOpcode.PTRADD, Ptradd),
        ("LABELBUILD", PcodeOpcode.PTRADD, Ptradd),
        ("CROSSBUILD", PcodeOpcode.PTRSUB, Ptrsub),
        ("MACROBUILD", PcodeOpcode.CAST, Cast),
    ],
)
def test_u031_bridge_canonicalizes_placeholder_pcode_aliases(
    raw_opcode: str,
    canonical_opcode: PcodeOpcode,
    expected_type: type[PcodeOpInfo],
) -> None:
    pcode_op = _coerce_pcode_op(
        {
            "id": 1,
            "opcode": raw_opcode,
            "instruction_address": 0x401000,
            "sequence_time": 0,
            "sequence_order": 0,
            "input_varnode_ids": [],
            "output_varnode_id": None,
        }
    )

    assert isinstance(pcode_op, expected_type)
    assert pcode_op.opcode is canonical_opcode


def test_u032_bridge_rejects_unknown_varnode_space() -> None:
    with pytest.raises(
        ValueError,
        match=r"Unknown varnode space 'unknown_space'. Update flatline.",
    ):
        _coerce_varnode_info(_make_varnode_payload(id=1, space="unknown_space", size=4))
