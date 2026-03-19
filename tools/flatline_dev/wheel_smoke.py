"""Installed-wheel smoke check used by cibuildwheel."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import flatline
from flatline import DecompileRequest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "fx_add_elf64.hex"
EXPECTED_NORMALIZED_C = (
    "int4 func_1000 ( int4 param_1 , int4 param_2 ) "
    "{ return param_1 + param_2 ; }"
)
_C_TOKEN_PATTERN = re.compile(
    r"0x[0-9a-fA-F]+|"
    r"[A-Za-z_][A-Za-z0-9_]*|"
    r"\d+|"
    r"==|!=|<=|>=|->|<<|>>|&&|\|\||"
    r"[{}()\[\];,:+\-*/%<>=&|^~!]"
)


def _load_memory_image() -> bytes:
    raw_hex = FIXTURE_PATH.read_text(encoding="ascii")
    return bytes.fromhex("".join(raw_hex.split()))


def _normalize_c_code(source: str) -> str:
    return " ".join(_C_TOKEN_PATTERN.findall(source))


def main() -> int:
    request = DecompileRequest(
        memory_image=_load_memory_image(),
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
    )
    result = flatline.decompile_function(request)

    if result.error is not None:
        print(f"wheel smoke failed with structured error: {result.error}", file=sys.stderr)
        return 1
    if result.c_code is None or result.function_info is None:
        print("wheel smoke did not produce decompile output", file=sys.stderr)
        return 1
    if _normalize_c_code(result.c_code) != EXPECTED_NORMALIZED_C:
        print("wheel smoke produced unexpected normalized C output", file=sys.stderr)
        return 1
    if result.metadata.get("language_id") != request.language_id:
        print("wheel smoke reported unexpected language_id metadata", file=sys.stderr)
        return 1
    if result.metadata.get("compiler_spec") != request.compiler_spec:
        print("wheel smoke reported unexpected compiler_spec metadata", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
