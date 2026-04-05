from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest

from flatline import (
    DecompileRequest,
    DecompileResult,
    DiagnosticFlags,
    Enriched,
    FunctionInfo,
    FunctionPrototype,
    InstructionInfo,
    ParameterInfo,
    Pcode,
    PcodeOpInfo,
    TypeInfo,
    VarnodeFlags,
    VarnodeInfo,
    WarningItem,
)
from flatline.xray._inputs import MemoryImageTarget, build_decompile_request

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def fixture_path(name: str = "fx_add_elf64.hex") -> Path:
    return FIXTURES_DIR / name


def fixture_bytes(name: str = "fx_add_elf64.hex") -> bytes:
    return fixture_path(name).read_bytes()


def fixture_target(
    name: str = "fx_add_elf64.hex",
    *,
    base_address: int = 0x1000,
    function_address: int = 0x1000,
    language_id: str = "x86:LE:64:default",
    compiler_spec: str | None = "gcc",
) -> MemoryImageTarget:

    return MemoryImageTarget(
        memory_path=fixture_path(name),
        base_address=base_address,
        function_address=function_address,
        language_id=language_id,
        compiler_spec=compiler_spec,
    )


def fixture_request(
    name: str = "fx_add_elf64.hex",
    *,
    base_address: int = 0x1000,
    function_address: int = 0x1000,
    language_id: str = "x86:LE:64:default",
    compiler_spec: str | None = "gcc",
) -> DecompileRequest:
    return build_decompile_request(
        fixture_target(
            name,
            base_address=base_address,
            function_address=function_address,
            language_id=language_id,
            compiler_spec=compiler_spec,
        )
    )


def make_sample_pcode() -> Pcode:
    flags_input = VarnodeFlags(
        is_constant=False,
        is_input=True,
        is_free=False,
        is_implied=False,
        is_explicit=True,
        is_read_only=False,
        is_persist=False,
        is_addr_tied=False,
    )
    flags_temp = VarnodeFlags(
        is_constant=False,
        is_input=False,
        is_free=False,
        is_implied=False,
        is_explicit=True,
        is_read_only=False,
        is_persist=False,
        is_addr_tied=False,
    )
    flags_constant = VarnodeFlags(
        is_constant=True,
        is_input=False,
        is_free=False,
        is_implied=False,
        is_explicit=False,
        is_read_only=False,
        is_persist=False,
        is_addr_tied=False,
    )
    return Pcode(
        pcode_ops=[
            PcodeOpInfo(
                id=0,
                opcode="INT_ADD",
                instruction_address=0x1000,
                sequence_time=1,
                sequence_order=1,
                input_varnode_ids=[0, 1],
                output_varnode_id=2,
            ),
            PcodeOpInfo(
                id=1,
                opcode="RETURN",
                instruction_address=0x1003,
                sequence_time=2,
                sequence_order=2,
                input_varnode_ids=[2],
                output_varnode_id=None,
            ),
        ],
        varnodes=[
            VarnodeInfo(
                id=0,
                space="register",
                offset=0x0,
                size=4,
                flags=flags_input,
                defining_op_id=None,
                use_op_ids=[0],
            ),
            VarnodeInfo(
                id=1,
                space="register",
                offset=0x8,
                size=4,
                flags=flags_input,
                defining_op_id=None,
                use_op_ids=[0],
            ),
            VarnodeInfo(
                id=2,
                space="unique",
                offset=0x100,
                size=4,
                flags=flags_temp,
                defining_op_id=0,
                use_op_ids=[1],
            ),
            VarnodeInfo(
                id=3,
                space="ram",
                offset=0x200,
                size=8,
                flags=flags_constant,
                defining_op_id=None,
                use_op_ids=[],
            ),
        ],
    )


def make_sample_result() -> DecompileResult:
    pcode = make_sample_pcode()
    function_info = FunctionInfo(
        name="add",
        entry_address=0x1000,
        size=16,
        is_complete=True,
        prototype=FunctionPrototype(
            calling_convention="__cdecl",
            parameters=[
                ParameterInfo(
                    name="a",
                    type=TypeInfo(name="int", size=4, metatype="int"),
                    index=0,
                    storage=None,
                ),
                ParameterInfo(
                    name="b",
                    type=TypeInfo(name="int", size=4, metatype="int"),
                    index=1,
                    storage=None,
                ),
            ],
            return_type=TypeInfo(name="int", size=4, metatype="int"),
            is_noreturn=False,
            has_this_pointer=False,
            has_input_errors=False,
            has_output_errors=False,
        ),
        local_variables=[],
        call_sites=[],
        jump_tables=[],
        diagnostics=DiagnosticFlags(
            is_complete=True,
            has_unreachable_blocks=False,
            has_unimplemented=False,
            has_bad_data=False,
            has_no_code=False,
        ),
        varnode_count=24,
    )
    return DecompileResult(
        c_code="int add(int a, int b) { return a + b; }",
        function_info=function_info,
        warnings=[WarningItem(code="analyze.W001", message="synthetic warning", phase="analyze")],
        error=None,
        metadata={
            "decompiler_version": "test",
            "language_id": "x86:LE:64:default",
            "compiler_spec": "gcc",
            "diagnostics": {},
        },
        enriched=Enriched(
            pcode=pcode,
            instructions=[
                InstructionInfo(address=0x1000, length=3, mnemonic="ADD", operands="EAX, EBX"),
                InstructionInfo(address=0x1003, length=1, mnemonic="RET", operands=""),
            ],
        ),
    )


def make_tkinter_stub() -> types.ModuleType:
    module = types.ModuleType("tkinter")

    class Tk:
        pass

    module.__dict__["Tk"] = Tk
    module.__dict__["TclError"] = RuntimeError
    module.__dict__["END"] = "end"
    module.__dict__["LAST"] = "last"
    module.__dict__["EXTENDED"] = "extended"
    return module


def import_graph_window(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    previous = monkeypatch.setitem(sys.modules, "tkinter", make_tkinter_stub())
    assert previous is None
    sys.modules.pop("flatline.xray._graph_window", None)  # pyright: ignore[reportUnusedCallResult]
    return importlib.import_module("flatline.xray._graph_window")
