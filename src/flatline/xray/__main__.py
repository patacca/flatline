"""Command-line entry point for flatline.xray.

The flatline.xray API is alpha and may change between minor releases without
deprecation notice.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from flatline.xray._inputs import (
    CAPSTONE_AVAILABLE,
    MemoryImageTarget,
    decompile_target,
    print_target_pairs,
)

_CAPSTONE_NOTE_EMITTED = False


def _parse_address(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid address: {value!r}") from exc


def _emit_capstone_note_once() -> None:
    global _CAPSTONE_NOTE_EMITTED
    if CAPSTONE_AVAILABLE or _CAPSTONE_NOTE_EMITTED:
        return
    print(
        "Note: capstone not found; assembly panel will show addresses only.\n"
        "      For disassembly: pip install flatline[xray]",
        file=sys.stderr,
    )
    _CAPSTONE_NOTE_EMITTED = True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flatline-xray",
        description="Open a flatline pcode graph viewer for one memory image target.",
    )
    parser.add_argument("memory_image", nargs="?", type=Path, help="Raw memory image file.")
    parser.add_argument(
        "--base-address",
        type=_parse_address,
        help="Virtual address of the first byte in memory_image.",
    )
    parser.add_argument(
        "--function-address",
        type=_parse_address,
        help="Entry-point address of the function to visualize.",
    )
    parser.add_argument(
        "--language-id",
        help="Ghidra language identifier for the target architecture.",
    )
    parser.add_argument(
        "--compiler-spec",
        default=None,
        help="Optional compiler specification name.",
    )
    parser.add_argument(
        "--runtime-data-dir",
        default=None,
        help="Optional explicit Ghidra runtime data directory.",
    )
    parser.add_argument(
        "--title",
        default="Flatline X-Ray",
        help="Window title.",
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="List available language/compiler pairs and exit.",
    )
    return parser


def _missing_required_args(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if args.memory_image is None:
        missing.append("memory_image")
    if args.base_address is None:
        missing.append("--base-address")
    if args.function_address is None:
        missing.append("--function-address")
    if args.language_id is None:
        missing.append("--language-id")
    return missing


def _main_with_args(args: argparse.Namespace) -> int:
    _emit_capstone_note_once()

    if args.list_targets:
        print_target_pairs(args.runtime_data_dir)
        return 0

    missing = _missing_required_args(args)
    if missing:
        print(
            "flatline-xray requires "
            + ", ".join(missing)
            + " unless --list-targets is set.",
            file=sys.stderr,
        )
        return 2

    target = MemoryImageTarget(
        memory_path=args.memory_image,
        base_address=args.base_address,
        function_address=args.function_address,
        language_id=args.language_id,
        compiler_spec=args.compiler_spec,
    )
    request, result = decompile_target(target, runtime_data_dir=args.runtime_data_dir)
    if result.error is not None:
        print(
            "flatline-xray could not decompile "
            f"{target.memory_path}: {result.error.category}: {result.error.message}",
            file=sys.stderr,
        )
        return 1

    from flatline.xray._graph_window import XrayWindow

    XrayWindow(
        args.title,
        result,
        request=request,
        source_label=str(target.memory_path),
    ).show()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return _main_with_args(args)


def _cli_entry() -> None:
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
