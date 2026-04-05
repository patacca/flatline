"""Shared bridge adapter test doubles and fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flatline._version import DECOMPILER_VERSION


class _NativeSessionSuccessDouble:
    """Native-session test double with tuple/list return shapes."""

    def __init__(self) -> None:
        self.closed = False
        self.last_request_payload: dict[str, Any] | None = None
        self.decompile_calls = 0

    def close(self) -> None:
        self.closed = True

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return [("x86:LE:64:default", "gcc")]

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        self.decompile_calls += 1
        self.last_request_payload = request_payload
        enriched = None
        if request_payload["enriched"]:
            enriched = {
                "instructions": [
                    {
                        "address": request_payload["function_address"],
                        "length": 3,
                        "mnemonic": "ADD",
                        "operands": "EAX, EBX",
                    }
                ],
                "pcode": {
                    "pcode_ops": [
                        {
                            "id": 0,
                            "opcode": "INT_ADD",
                            "instruction_address": request_payload["function_address"],
                            "sequence_time": 1,
                            "sequence_order": 0,
                            "input_varnode_ids": [0, 1],
                            "output_varnode_id": 2,
                        },
                        {
                            "id": 1,
                            "opcode": "RETURN",
                            "instruction_address": request_payload["function_address"] + 3,
                            "sequence_time": 2,
                            "sequence_order": 1,
                            "input_varnode_ids": [2],
                            "output_varnode_id": None,
                        },
                    ],
                    "varnodes": [
                        {
                            "id": 0,
                            "space": "register",
                            "offset": 0x0,
                            "size": 4,
                            "flags": {
                                "is_constant": False,
                                "is_input": True,
                                "is_free": False,
                                "is_implied": False,
                                "is_explicit": True,
                                "is_read_only": False,
                                "is_persist": False,
                                "is_addr_tied": False,
                            },
                            "defining_op_id": None,
                            "use_op_ids": [0],
                        },
                        {
                            "id": 1,
                            "space": "register",
                            "offset": 0x8,
                            "size": 4,
                            "flags": {
                                "is_constant": False,
                                "is_input": True,
                                "is_free": False,
                                "is_implied": False,
                                "is_explicit": True,
                                "is_read_only": False,
                                "is_persist": False,
                                "is_addr_tied": False,
                            },
                            "defining_op_id": None,
                            "use_op_ids": [0],
                        },
                        {
                            "id": 2,
                            "space": "unique",
                            "offset": 0x100,
                            "size": 4,
                            "flags": {
                                "is_constant": False,
                                "is_input": False,
                                "is_free": False,
                                "is_implied": False,
                                "is_explicit": True,
                                "is_read_only": False,
                                "is_persist": False,
                                "is_addr_tied": False,
                            },
                            "defining_op_id": 0,
                            "use_op_ids": [1],
                        },
                    ],
                }
            }
        return {
            "c_code": "int add(int a, int b) { return a + b; }",
            "function_info": {
                "name": "add",
                "entry_address": 0x1000,
                "size": 16,
                "is_complete": True,
                "prototype": {
                    "calling_convention": "__cdecl",
                    "parameters": [
                        {
                            "name": "a",
                            "type": {"name": "int", "size": 4, "metatype": "int"},
                            "index": 0,
                            "storage": None,
                        },
                        {
                            "name": "b",
                            "type": {"name": "int", "size": 4, "metatype": "int"},
                            "index": 1,
                            "storage": None,
                        },
                    ],
                    "return_type": {"name": "int", "size": 4, "metatype": "int"},
                    "is_noreturn": False,
                    "has_this_pointer": False,
                    "has_input_errors": False,
                    "has_output_errors": False,
                },
                "local_variables": [],
                "call_sites": [],
                "jump_tables": [],
                "diagnostics": {
                    "is_complete": True,
                    "has_unreachable_blocks": False,
                    "has_unimplemented": False,
                    "has_bad_data": False,
                    "has_no_code": False,
                },
                "varnode_count": 24,
            },
            "warnings": [
                {
                    "code": "analyze.W001",
                    "message": "synthetic warning",
                    "phase": "analyze",
                }
            ],
            "error": None,
            "metadata": {
                "decompiler_version": DECOMPILER_VERSION,
                "language_id": request_payload["language_id"],
                "compiler_spec": request_payload["compiler_spec"] or "",
                "diagnostics": {},
            },
            "enriched": enriched,
        }


class _NativeSessionFailureDouble:
    """Native-session test double that raises in decompile."""

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return [("x86:LE:64:default", "gcc")]

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("native bridge failure at /tmp/native/session.log")

    def close(self) -> None:
        return None


class _NativeSessionInvalidSuccessShapeDouble:
    """Native-session test double returning a malformed success payload."""

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return [("x86:LE:64:default", "gcc")]

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "c_code": "int add(int a, int b) { return a + b; }",
            "function_info": None,
            "warnings": [],
            "error": None,
            "metadata": {
                "decompiler_version": DECOMPILER_VERSION,
                "language_id": request_payload["language_id"],
                "compiler_spec": request_payload["compiler_spec"] or "",
                "diagnostics": {},
            },
        }

    def close(self) -> None:
        return None


class _NativeSessionMissingEnrichedDouble(_NativeSessionSuccessDouble):
    """Native-session double that omits opt-in enriched payloads."""

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        result = super().decompile_function(request_payload)
        result.pop("enriched", None)
        return result


class _NativeSessionMissingPcodeDouble(_NativeSessionSuccessDouble):
    """Native-session double that returns enriched with pcode missing."""

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        result = super().decompile_function(request_payload)
        if result.get("enriched") is not None:
            result["enriched"] = {"pcode": None}
        return result


class _NativeSessionEmptyEnumerationDouble:
    """Native-session double with empty enumeration output.

    Used to verify runtime-data-backed fallback enumeration in bridge adapters.
    """

    def __init__(self) -> None:
        self.decompile_calls = 0

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return []

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        self.decompile_calls += 1
        return {
            "c_code": None,
            "function_info": None,
            "warnings": [],
            "error": {
                "category": "internal_error",
                "message": "native bridge skeleton: decompile pipeline not implemented",
                "retryable": False,
            },
            "metadata": {
                "decompiler_version": DECOMPILER_VERSION,
                "language_id": request_payload["language_id"],
                "compiler_spec": request_payload["compiler_spec"] or "",
                "diagnostics": {},
            },
        }

    def close(self) -> None:
        return None


class _NativeModuleDouble:
    """Module-level test double exposing create_session."""

    def __init__(self, native_session: Any) -> None:
        self.native_session = native_session
        self.runtime_data_dir: str | None = None

    def create_session(self, runtime_data_dir: str | None = None) -> Any:
        self.runtime_data_dir = runtime_data_dir
        return self.native_session


def _make_runtime_data_fixture(tmp_path: Path) -> Path:
    """Create a synthetic runtime-data directory with one valid pair.

    Includes one compiler entry whose backing spec file exists and one whose
    spec file is missing, allowing existence filtering assertions.
    """
    runtime_dir = tmp_path / "runtime_data"
    language_dir = runtime_dir / "languages"
    language_dir.mkdir(parents=True)

    (language_dir / "x86-gcc.cspec").write_text("<compiler_spec/>", encoding="ascii")
    (language_dir / "x86.ldefs").write_text(
        (
            "<language_definitions>\n"
            '  <language id="x86:LE:64:default">\n'
            '    <compiler name="gcc" spec="x86-gcc.cspec"/>\n'
            '    <compiler name="broken" spec="missing.cspec"/>\n'
            "  </language>\n"
            "</language_definitions>\n"
        ),
        encoding="ascii",
    )
    return runtime_dir
