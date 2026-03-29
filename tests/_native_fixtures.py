"""Shared fixture metadata and helpers for native test coverage."""

from __future__ import annotations

import hashlib
import re
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from os import fspath
from pathlib import Path

from flatline import DecompileRequest, DecompileResult, DecompilerSession

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"

_C_TOKEN_PATTERN = re.compile(
    r"0x[0-9a-fA-F]+|"
    r"[A-Za-z_][A-Za-z0-9_]*|"
    r"\d+|"
    r"==|!=|<=|>=|->|<<|>>|&&|\|\||"
    r"[{}()\[\];,:+\-*/%<>=&|^~!]"
)


@dataclass(frozen=True)
class NativeFixture:
    """One committed native decompile fixture."""

    fixture_id: str
    language_id: str
    compiler_spec: str
    hex_filename: str
    sha256: str
    normalized_c: str
    expected_function_size: int
    expected_param_count: int
    expected_return_type_name: str
    expected_return_type_size: int
    expected_return_type_metatype: str
    expected_varnode_count: int
    expected_warning_count: int = 0
    warm_p95_budget_seconds: float | None = None
    expected_jump_table_switch_address: int | None = None
    expected_jump_table_targets: tuple[int, ...] = ()
    base_address: int = 0x1000
    function_address: int = 0x1000

    @property
    def hex_path(self) -> Path:
        return FIXTURE_DIR / self.hex_filename

    def memory_image(self) -> bytes:
        raw_hex = self.hex_path.read_text(encoding="ascii")
        memory_image = bytes.fromhex("".join(raw_hex.split()))
        digest = hashlib.sha256(memory_image).hexdigest()
        if digest != self.sha256:
            raise AssertionError(
                f"{self.fixture_id} sha256 mismatch: expected {self.sha256}, got {digest}"
            )
        return memory_image

    def build_request(
        self,
        runtime_data_dir: str,
        *,
        enriched: bool = False,
        tail_padding: bytes | None = b"\x00",
    ) -> DecompileRequest:
        return DecompileRequest(
            memory_image=self.memory_image(),
            base_address=self.base_address,
            function_address=self.function_address,
            language_id=self.language_id,
            compiler_spec=self.compiler_spec,
            runtime_data_dir=runtime_data_dir,
            enriched=enriched,
            tail_padding=tail_padding,
        )


FIXTURE_IDS: tuple[str, ...] = (
    "fx_add_elf64",
    "fx_add_elf32",
    "fx_add_arm64",
    "fx_add_riscv64",
    "fx_add_mips32",
    "fx_switch_elf64",
    "fx_warning_elf64",
)

MULTI_ISA_FIXTURE_IDS: tuple[str, ...] = (
    "fx_add_elf32",
    "fx_add_arm64",
    "fx_add_riscv64",
    "fx_add_mips32",
)

PERFORMANCE_FIXTURE_IDS: tuple[str, ...] = (
    "fx_add_elf64",
    "fx_add_elf32",
    "fx_add_arm64",
    "fx_add_riscv64",
    "fx_add_mips32",
    "fx_switch_elf64",
)


_FIXTURES: dict[str, NativeFixture] = {
    "fx_add_elf64": NativeFixture(
        fixture_id="fx_add_elf64",
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
        hex_filename="fx_add_elf64.hex",
        sha256="c256c0e67b4e9c9493982d00effc6ece20d1e296312034b675e35f72959b2ddb",
        normalized_c=(
            "int4 func_1000 ( int4 param_1 , int4 param_2 ) { return param_1 + param_2 ; }"
        ),
        expected_function_size=4,
        expected_param_count=2,
        expected_return_type_name="int4",
        expected_return_type_size=4,
        expected_return_type_metatype="int",
        expected_varnode_count=5,
        warm_p95_budget_seconds=0.05,
    ),
    "fx_add_elf32": NativeFixture(
        fixture_id="fx_add_elf32",
        language_id="x86:LE:32:default",
        compiler_spec="gcc",
        hex_filename="fx_add_elf32.hex",
        sha256="d3d3e02046fef3b2cd6baab50c71b221996d84c2526a750cc15b4a33a79a8f24",
        normalized_c=(
            "int4 func_1000 ( int4 param_1 , int4 param_2 ) { return param_1 + param_2 ; }"
        ),
        expected_function_size=9,
        expected_param_count=2,
        expected_return_type_name="int4",
        expected_return_type_size=4,
        expected_return_type_metatype="int",
        expected_varnode_count=4,
        warm_p95_budget_seconds=0.05,
    ),
    "fx_add_arm64": NativeFixture(
        fixture_id="fx_add_arm64",
        language_id="AARCH64:LE:64:v8A",
        compiler_spec="default",
        hex_filename="fx_add_arm64.hex",
        sha256="9bfea10d7217396fb690a5727f3716948b218e9457c513a9c551642286e6d330",
        normalized_c=(
            "int4 func_1000 ( int4 param_1 , int4 param_2 ) { return param_1 + param_2 ; }"
        ),
        expected_function_size=8,
        expected_param_count=2,
        expected_return_type_name="int4",
        expected_return_type_size=4,
        expected_return_type_metatype="int",
        expected_varnode_count=5,
        warm_p95_budget_seconds=0.05,
    ),
    "fx_add_riscv64": NativeFixture(
        fixture_id="fx_add_riscv64",
        language_id="RISCV:LE:64:RV64I",
        compiler_spec="gcc",
        hex_filename="fx_add_riscv64.hex",
        sha256="a6318f84d1179297aac08cca3a0bcbf7b630202a7dc88363f28268d6501189b5",
        normalized_c=(
            "int8 func_1000 ( int4 param_1 , int4 param_2 ) "
            "{ return ( int8 ) ( param_1 + param_2 ) ; }"
        ),
        expected_function_size=4,
        expected_param_count=2,
        expected_return_type_name="int8",
        expected_return_type_size=8,
        expected_return_type_metatype="int",
        expected_varnode_count=5,
        warm_p95_budget_seconds=0.075,
    ),
    "fx_add_mips32": NativeFixture(
        fixture_id="fx_add_mips32",
        language_id="MIPS:LE:32:default",
        compiler_spec="default",
        hex_filename="fx_add_mips32.hex",
        sha256="f312dbb7760a8c39a3582b09630b667d3999da7daa72a77ede41847397d1d14f",
        normalized_c=(
            "int4 func_1000 ( int4 param_1 , int4 param_2 ) { return param_1 + param_2 ; }"
        ),
        expected_function_size=12,
        expected_param_count=2,
        expected_return_type_name="int4",
        expected_return_type_size=4,
        expected_return_type_metatype="int",
        expected_varnode_count=4,
        warm_p95_budget_seconds=0.05,
    ),
    "fx_switch_elf64": NativeFixture(
        fixture_id="fx_switch_elf64",
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
        hex_filename="fx_switch_elf64.hex",
        sha256="4c0dd28c39f5dd587bac1c842e21260cfdf7473c237f9d12f981f98cc2aa0b2b",
        normalized_c=(
            "uint4 func_1000 ( xunknown4 param_1 , uint4 param_2 ) "
            "{ switch ( param_1 ) { case 0 : return param_2 + 0xb ; "
            "case 1 : return param_2 * 3 - 1 ; case 2 : return param_2 ^ 0x1234 ; "
            "case 3 : return ( int4 ) param_2 / 3 ; case 4 : return param_2 << 2 ; "
            "case 5 : return param_2 - 0x4d ; case 6 : return param_2 * param_2 ; "
            "case 7 : return ( int4 ) param_2 % 5 ; default : return 0xffffffff ; } }"
        ),
        expected_function_size=101,
        expected_param_count=2,
        expected_return_type_name="uint4",
        expected_return_type_size=4,
        expected_return_type_metatype="uint",
        expected_varnode_count=40,
        warm_p95_budget_seconds=0.1,
        expected_jump_table_switch_address=0x1009,
        expected_jump_table_targets=(
            0x1010,
            0x1051,
            0x1018,
            0x101E,
            0x1014,
            0x1057,
            0x105B,
            0x1035,
            0x105F,
        ),
    ),
    "fx_warning_elf64": NativeFixture(
        fixture_id="fx_warning_elf64",
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
        hex_filename="fx_warning_elf64.hex",
        sha256="ab27713e0e565347fb65a1c2e241240a235cfad69e73d4cc06b12d2ebf41eecc",
        normalized_c=(
            "xunknown8 func_1000 ( int8 param_1 ) { xunknown8 xVar1 ; "
            "if ( ( uint4 ) param_1 < 4 ) { / * WARNING : Could not recover jumptable "
            "at 0x00001013 Too many branches * / / * WARNING : Treating indirect jump "
            "as call * / xVar1 = ( * ( code * ) ( ( int8 ) * ( int4 * ) "
            "( param_1 * 4 + 0x1034 ) + 0x1034 ) ) ( ) ; return xVar1 ; } "
            "return 0xffffffff ; }"
        ),
        expected_function_size=51,
        expected_param_count=1,
        expected_return_type_name="xunknown8",
        expected_return_type_size=8,
        expected_return_type_metatype="unknown",
        expected_varnode_count=22,
        expected_warning_count=2,
    ),
}


def get_native_fixture(fixture_id: str) -> NativeFixture:
    """Return one committed fixture definition by id."""
    try:
        return _FIXTURES[fixture_id]
    except KeyError as exc:  # pragma: no cover - test misuse guard
        raise ValueError(f"unknown native fixture: {fixture_id}") from exc


def get_native_runtime_data_dir() -> str:
    """Return the installed `ghidra_sleigh` runtime-data root as a string."""
    try:
        import ghidra_sleigh
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("ghidra-sleigh is not installed in this environment") from exc
    return fspath(ghidra_sleigh.get_runtime_data_dir())


def normalize_c_code(c_code: str) -> str:
    """Normalize formatting-only drift from decompiler C output."""
    return " ".join(_C_TOKEN_PATTERN.findall(c_code))


def assert_successful_result(result: DecompileResult) -> None:
    """Assert the contract shape for a successful decompile result."""
    assert result.error is None
    assert result.c_code is not None
    assert result.function_info is not None


@contextmanager
def open_native_session(runtime_data_dir: str) -> Iterator[DecompilerSession]:
    """Open a session while ignoring the vendored mock `.ldefs` warning."""
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=(
                r"Skipped malformed \.ldefs files while enumerating runtime data"
                r".*mock\.ldefs.*"
            ),
            category=RuntimeWarning,
        )
        with DecompilerSession(runtime_data_dir=runtime_data_dir) as session:
            yield session
