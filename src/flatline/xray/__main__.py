"""Command-line entry point for flatline.xray.

The flatline.xray API is alpha and may change between minor releases without
deprecation notice.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from flatline.xray._inputs import (
    MemoryImageTarget,
    decompile_target,
    print_target_pairs,
)

if TYPE_CHECKING:
    from flatline.models import DecompileResult
    from flatline.xray._layout import LayoutResult


def _parse_address(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid address: {value!r}") from exc


def _format_user_facing_error(
    exc: Exception,
    *,
    input_path: Path | None = None,
) -> str:
    prefix = "flatline-xray could not start"
    if input_path is not None:
        prefix += f" for {input_path}"
    return (
        f"{prefix}: {exc}\n"
        "Ensure ghidra-sleigh is installed (`pip install flatline`), "
        "pass --runtime-data-dir if auto-discovery is unavailable, and "
        "verify the target/address flags."
    )


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
        "--function",
        dest="function_alias",
        type=_parse_address,
        default=None,
        help="Alias for --function-address (used by --layout-dump).",
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
    parser.add_argument(
        "--cpg",
        action="store_true",
        default=False,
        help="Enable Code Property Graph mode (control-flow edges).",
    )
    parser.add_argument(
        "--layout-dump",
        type=Path,
        default=None,
        metavar="MEMORY_IMAGE",
        help="Headless mode: compute layout + routes for MEMORY_IMAGE; write JSON to --out.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON path for --layout-dump mode.",
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


def _resolve_function_address(args: argparse.Namespace) -> int | None:
    # --function is an alias accepted for the layout-dump CLI surface.
    if args.function_address is not None:
        return args.function_address
    return args.function_alias


def _build_layout_payload(
    layout: LayoutResult,
    routes: dict,
) -> dict:
    # back_edges in meta are (src_str, dst_str) 2-tuples (no edge key).
    back_edge_pairs = {tuple(pair) for pair in layout.meta.get("back_edges", [])}
    nodes_payload = {
        node_key: {"x": pos.x, "y": pos.y, "w": pos.w, "h": pos.h}
        for node_key, pos in layout.nodes.items()
    }
    edges_payload = []
    for (src, dst, key), polyline in routes.items():
        src_str = repr(src)
        dst_str = repr(dst)
        edges_payload.append(
            {
                "src": src_str,
                "dst": dst_str,
                "key": repr(key),
                "polyline": [[float(x), float(y)] for x, y in polyline],
                "back_edge": (src_str, dst_str) in back_edge_pairs,
            }
        )
    return {
        "schema_version": 1,
        "nodes": nodes_payload,
        "edges": edges_payload,
    }


def _layout_dump_missing_args(args: argparse.Namespace, function_address: int | None) -> list[str]:
    missing: list[str] = []
    if function_address is None:
        missing.append("--function (or --function-address)")
    if args.out is None:
        missing.append("--out")
    if args.language_id is None:
        missing.append("--language-id")
    if args.base_address is None:
        missing.append("--base-address")
    return missing


def _load_memory_image(path: Path) -> bytes:
    # .hex fixtures store an ASCII hex dump; raw paths are read verbatim.
    if path.suffix.lower() == ".hex":
        return bytes.fromhex("".join(path.read_text(encoding="ascii").split()))
    return path.read_bytes()


def _run_layout_dump(args: argparse.Namespace) -> int:
    fixture_path: Path = args.layout_dump
    if not fixture_path.exists():
        print(
            f"flatline-xray --layout-dump: file not found: {fixture_path}",
            file=sys.stderr,
        )
        return 1

    function_address = _resolve_function_address(args)
    missing = _layout_dump_missing_args(args, function_address)
    if missing:
        print(
            "flatline-xray --layout-dump requires " + ", ".join(missing) + ".",
            file=sys.stderr,
        )
        return 2

    try:
        memory_image = _load_memory_image(fixture_path)
        result = _decompile_for_dump(
            memory_image=memory_image,
            base_address=args.base_address,
            function_address=function_address,
            language_id=args.language_id,
            compiler_spec=args.compiler_spec,
            runtime_data_dir=args.runtime_data_dir,
        )
    except Exception as exc:
        print(
            _format_user_facing_error(exc, input_path=fixture_path),
            file=sys.stderr,
        )
        return 2

    if result.error is not None:
        print(
            "flatline-xray --layout-dump could not decompile "
            f"{fixture_path}: {result.error.category}: {result.error.message}",
            file=sys.stderr,
        )
        return 2

    try:
        payload = _compute_dump_payload(result)
    except Exception as exc:
        print(
            f"flatline-xray --layout-dump: layout/routing failed: {exc}",
            file=sys.stderr,
        )
        return 2

    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return 0


def _compute_dump_payload(result: DecompileResult) -> dict:
    # Lazy imports so default flatline-xray invocation does not pay for native bridge.
    from flatline.xray._edge_routing import route_edges
    from flatline.xray._layout import compute_layout

    if result.enriched is None or result.enriched.pcode is None:
        raise RuntimeError("decompile result missing enriched pcode")
    pcode_graph = result.enriched.pcode.to_graph()
    layout = compute_layout(pcode_graph)
    routes = route_edges(layout, pcode_graph)
    return _build_layout_payload(layout, routes)


def _decompile_for_dump(
    *,
    memory_image: bytes,
    base_address: int,
    function_address: int,
    language_id: str,
    compiler_spec: str | None,
    runtime_data_dir: str | None,
) -> DecompileResult:
    from flatline import DecompileRequest, decompile_function

    request = DecompileRequest(
        memory_image=memory_image,
        base_address=base_address,
        function_address=function_address,
        language_id=language_id,
        compiler_spec=compiler_spec,
        runtime_data_dir=runtime_data_dir,
        enriched=True,
    )
    return decompile_function(request)


def _main_with_args(args: argparse.Namespace) -> int:
    if args.list_targets:
        print_target_pairs(args.runtime_data_dir)
        return 0

    if args.layout_dump is not None:
        return _run_layout_dump(args)

    try:
        missing = _missing_required_args(args)
        if missing:
            print(
                "flatline-xray requires " + ", ".join(missing) + " unless --list-targets is set.",
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
            cpg=args.cpg,
            function_info=result.function_info,
        ).show()
    except Exception as exc:
        print(
            _format_user_facing_error(exc, input_path=args.memory_image),
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return _main_with_args(args)


def _cli_entry() -> None:
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
