"""Input and request helpers for flatline.xray.

This module stays free of tkinter so it can be imported in headless
environments and by CLI-only code paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from flatline import DecompileRequest, DecompileResult, decompile_function, list_language_compilers
from flatline.models import LanguageCompilerPair

if TYPE_CHECKING:
    from collections.abc import Iterable

    from flatline.models.types import InstructionInfo


@dataclass(frozen=True)
class MemoryImageTarget:
    """One xray target backed by a caller-provided memory image."""

    memory_path: Path
    base_address: int
    function_address: int
    language_id: str
    compiler_spec: str | None = None

    def read_memory_image(self) -> bytes:
        """Read the raw memory image bytes from disk."""
        return Path(self.memory_path).read_bytes()


def build_decompile_request(
    target: MemoryImageTarget,
    *,
    runtime_data_dir: str | Path | None = None,
    enriched: bool = True,
) -> DecompileRequest:
    """Build a decompile request for one xray target."""
    return DecompileRequest(
        memory_image=target.read_memory_image(),
        base_address=target.base_address,
        function_address=target.function_address,
        language_id=target.language_id,
        compiler_spec=target.compiler_spec,
        runtime_data_dir=str(runtime_data_dir) if runtime_data_dir is not None else None,
        enriched=enriched,
    )


def decompile_target(
    target: MemoryImageTarget,
    *,
    runtime_data_dir: str | Path | None = None,
    enriched: bool = True,
) -> tuple[DecompileRequest, DecompileResult]:
    """Build and run a decompilation request for one xray target."""
    request = build_decompile_request(
        target,
        runtime_data_dir=runtime_data_dir,
        enriched=enriched,
    )
    result = decompile_function(request)
    return request, result


def list_target_pairs(
    runtime_data_dir: str | Path | None = None,
) -> list[LanguageCompilerPair]:
    """Enumerate valid language/compiler pairs for xray target discovery."""
    return list_language_compilers(runtime_data_dir)


def format_target_pair(pair: LanguageCompilerPair) -> str:
    """Render one language/compiler pair for CLI display."""
    return f"{pair.language_id} {pair.compiler_spec}"


def iter_target_lines(
    runtime_data_dir: str | Path | None = None,
) -> Iterable[str]:
    """Yield one formatted target line per discovered pair."""
    for pair in list_target_pairs(runtime_data_dir):
        yield format_target_pair(pair)


def print_target_pairs(runtime_data_dir: str | Path | None = None) -> None:
    """Print discovered language/compiler pairs one per line."""
    for line in iter_target_lines(runtime_data_dir):
        print(line)


def disassemble_instruction_addresses(
    instructions: list[InstructionInfo] | None,
) -> list[tuple[int, str]]:
    """Render instruction lines for the assembly panel."""
    if not instructions:
        return []
    return [
        (instr.address, f"0x{instr.address:x}:  {instr.mnemonic} {instr.operands}".strip())
        for instr in instructions
    ]


def _opcode_color(opcode: str) -> str:
    if opcode.startswith(("INT_", "BOOL_", "FLOAT_")):
        return "#ff9f68"
    if opcode.startswith(("LOAD", "STORE")):
        return "#f28482"
    if opcode in {"BRANCH", "CBRANCH", "BRANCHIND"}:
        return "#ffd166"
    if opcode in {"CALL", "CALLIND", "RETURN"}:
        return "#ff6b6b"
    return "#8ecae6"


def _varnode_color(varnode) -> str:
    if varnode.flags.is_constant:
        return "#ffd166"
    if varnode.flags.is_input:
        return "#72ddf7"
    if varnode.flags.is_persist or varnode.flags.is_addr_tied:
        return "#95d5b2"
    if varnode.flags.is_read_only:
        return "#caffbf"
    return "#98f5e1"


def _short_opcode(opcode: str) -> str:
    if "_" in opcode:
        head, tail = opcode.split("_", 1)
        return f"{head}\n{tail}"
    if len(opcode) > 10:
        return f"{opcode[:10]}\n{opcode[10:16]}"
    return opcode


def _varnode_badge(varnode) -> str:
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

