"""Command-line interface for the xray layout benchmark.

Subcommands:
    run     -- execute one or more adapters against one or more binaries.
    grid    -- compose a side-by-side PNG grid from per-adapter renders.
    report  -- regenerate the aggregate Markdown report (stub).
    check   -- probe each adapter's install_check() and print status.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


# Canonical adapter list shared across subcommands. Order matters for status
# tables and grid composition (matches the schema enum order).
ADAPTER_NAMES: list[str] = [
    "libavoid",
    "hola",
    "ogdf",
    "domus",
    "wueortho",
    "ogdf_libavoid",
]

# Repo-relative anchors. The benchmark lives at benchmarks/xray_layout/, so
# we walk up three parents from this file: cli.py -> bench -> xray_layout.
BENCH_ROOT = Path(__file__).resolve().parent
XRAY_LAYOUT_ROOT = BENCH_ROOT.parent
DEFAULT_OUT = XRAY_LAYOUT_ROOT / "out"
CORPUS_DIR = XRAY_LAYOUT_ROOT / "corpus"
SCHEMA_PATH = XRAY_LAYOUT_ROOT / "schemas" / "run.json"


def _adapter_class_name(name: str) -> str:
    """Map adapter module stem to its class name (e.g. ogdf_libavoid -> OgdfLibavoidAdapter)."""
    parts = name.split("_")
    return "".join(p.capitalize() for p in parts) + "Adapter"


def _load_adapter(name: str) -> tuple[Any | None, str | None]:
    """Try to import and instantiate the adapter named *name*.

    Returns:
        (instance, None) on success, or (None, error_message) on failure.
    """
    try:
        mod = importlib.import_module(
            f"benchmarks.xray_layout.bench.adapters.{name}_adapter"
        )
    except ImportError as exc:
        return None, f"adapter module not found ({exc})"
    cls_name = _adapter_class_name(name)
    cls = getattr(mod, cls_name, None)
    if cls is None:
        # Fallback: scan module for a class ending in 'Adapter'.
        for attr in dir(mod):
            if attr.endswith("Adapter") and attr != "Adapter":
                cls = getattr(mod, attr)
                break
    if cls is None:
        return None, f"no Adapter class in module (expected {cls_name})"
    try:
        return cls(), None
    except Exception as exc:  # noqa: BLE001 - want full diagnostic
        return None, f"adapter constructor raised: {exc}"


def _resolve_binary(binary: str) -> Path:
    """Resolve *binary* to a concrete path.

    Accepts either a corpus stem (matched against CORPUS_DIR/sources/<stem>.c)
    or an absolute/relative filesystem path.
    """
    p = Path(binary)
    if p.exists():
        return p.resolve()
    candidate = CORPUS_DIR / "sources" / f"{binary}.c"
    if candidate.exists():
        return candidate.resolve()
    # Last-ditch: treat as path even if missing; downstream will report.
    return p.resolve()


def _list_corpus_stems() -> list[str]:
    """Return sorted corpus stems (without extension)."""
    sources = CORPUS_DIR / "sources"
    if not sources.is_dir():
        return []
    return sorted(p.stem for p in sources.glob("*.c"))


def _machine_info() -> dict[str, Any]:
    """Best-effort hardware/OS description for run records."""
    info: dict[str, Any] = {
        "cpu": platform.processor() or platform.machine(),
        "os": f"{platform.system()} {platform.release()}",
    }
    try:
        import os as _os

        pages = _os.sysconf("SC_PHYS_PAGES")
        page_size = _os.sysconf("SC_PAGE_SIZE")
        info["ram_gb"] = round((pages * page_size) / (1024**3), 2)
    except (AttributeError, ValueError, OSError):
        pass
    return info


def _validate_record(record: dict[str, Any]) -> tuple[bool, str]:
    """Validate *record* against schemas/run.json.

    Falls back to a minimal structural check if jsonschema is unavailable.
    """
    try:
        import jsonschema
    except ImportError:
        # Minimal sanity check: required top-level keys.
        required = {"candidate", "binary", "function", "status"}
        missing = required - record.keys()
        if missing:
            return False, f"missing keys: {sorted(missing)}"
        return True, ""
    try:
        schema = json.loads(SCHEMA_PATH.read_text())
        jsonschema.validate(record, schema)
    except jsonschema.ValidationError as exc:
        return False, str(exc.message)
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"schema unreadable: {exc}"
    return True, ""


def _write_record(out_dir: Path, record: dict[str, Any]) -> Path:
    """Validate then write *record* under out_dir/runs/."""
    ok, msg = _validate_record(record)
    if not ok:
        raise ValueError(f"invalid run record: {msg}")
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{record['candidate']}__{record['binary']}__{record['function']}.json"
    path = runs_dir / fname
    path.write_text(json.dumps(record, indent=2, sort_keys=True))
    return path


def _run_one(
    adapter_name: str,
    binary_stem: str,
    binary_path: Path,
    entry: str | None,
    budget: int,
    out_dir: Path,
) -> dict[str, Any]:
    """Execute a single (adapter, binary) pair and return its run record."""
    record: dict[str, Any] = {
        "candidate": adapter_name,
        "binary": binary_stem,
        "function": entry or "<auto>",
        "status": "deferred",
        "machine": _machine_info(),
    }

    instance, err = _load_adapter(adapter_name)
    if instance is None:
        record["status"] = "deferred"
        record["error_message"] = err or "adapter unavailable"
        return record

    # Try to invoke the adapter's run method; tolerate any failure mode.
    try:
        # Adapter contract is still being finalised; we call run(...) if it
        # exists, otherwise mark the run as deferred so the harness keeps
        # going. Each adapter is expected to honour the time budget itself
        # or via the time_budget helper.
        run_fn = getattr(instance, "run", None)
        if run_fn is None:
            record["status"] = "deferred"
            record["error_message"] = "adapter has no run() method"
            return record
        result = run_fn(
            binary_path=binary_path,
            entry=entry,
            budget_seconds=budget,
            out_dir=out_dir,
        )
        if isinstance(result, dict):
            record.update(result)
        record.setdefault("status", "ok")
    except TimeoutError as exc:
        record["status"] = "timeout"
        record["error_message"] = str(exc)
    except MemoryError as exc:
        record["status"] = "crashed"
        record["error_message"] = f"OOM: {exc}"
    except Exception as exc:  # noqa: BLE001 - harness must not abort
        record["status"] = "error"
        record["error_message"] = f"{type(exc).__name__}: {exc}"
        # Stash trace as a side-band file; not part of schema.
        try:
            (out_dir / "errors").mkdir(parents=True, exist_ok=True)
            (out_dir / "errors" / f"{adapter_name}__{binary_stem}.txt").write_text(
                traceback.format_exc()
            )
        except OSError:
            pass
    return record


def _split_csv(value: str | None, default: list[str]) -> list[str]:
    """Parse a comma-separated value supporting the literal 'all'."""
    if value is None:
        return default
    if value.strip().lower() == "all":
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


def cmd_run(args: argparse.Namespace) -> int:
    """Execute selected (candidate x input) combinations."""
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus_stems = _list_corpus_stems()
    # --binary takes precedence over --inputs.
    if args.binary is not None:
        binary_arg = args.binary
        resolved = _resolve_binary(binary_arg)
        binaries: list[tuple[str, Path]] = [(resolved.stem, resolved)]
    else:
        names = _split_csv(args.inputs, corpus_stems)
        binaries = [(stem, _resolve_binary(stem)) for stem in names]

    # --candidate (singular) takes precedence over --candidates (plural).
    if args.candidate is not None:
        candidates = [args.candidate]
    else:
        candidates = _split_csv(args.candidates, ADAPTER_NAMES)

    if not binaries:
        print("no binaries selected; aborting", file=sys.stderr)
        return 2
    if not candidates:
        print("no candidates selected; aborting", file=sys.stderr)
        return 2

    written = 0
    for adapter_name in candidates:
        for stem, path in binaries:
            record = _run_one(
                adapter_name=adapter_name,
                binary_stem=stem,
                binary_path=path,
                entry=args.entry,
                budget=args.budget,
                out_dir=out_dir,
            )
            try:
                dest = _write_record(out_dir, record)
                print(f"[{record['status']:8s}] {adapter_name} / {stem} -> {dest}")
                written += 1
            except ValueError as exc:
                print(
                    f"[skip] invalid record for {adapter_name}/{stem}: {exc}",
                    file=sys.stderr,
                )
    print(f"wrote {written} run record(s) to {out_dir / 'runs'}")
    return 0


def cmd_grid(args: argparse.Namespace) -> int:
    """Compose a side-by-side PNG grid for one binary across all adapters."""
    from .render import compose_grid

    out_dir = DEFAULT_OUT
    renders = out_dir / "renders"
    renders.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = []
    labels: list[str] = []
    for name in ADAPTER_NAMES:
        candidate = renders / f"{args.binary}__{name}.png"
        if candidate.exists():
            paths.append(candidate)
            labels.append(name)
        else:
            print(f"[miss] no render for {name}/{args.binary}", file=sys.stderr)

    if not paths:
        print("no per-adapter renders found; nothing to compose", file=sys.stderr)
        return 1

    out_path = renders / f"{args.binary}__GRID.png"
    compose_grid(paths, labels, out_path)
    print(f"wrote {out_path}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Aggregate every run record under ``out/runs`` into ``out/REPORT.md``."""
    from .report import generate

    out_dir = Path(args.out).resolve() if getattr(args, "out", None) else DEFAULT_OUT
    try:
        generate(out_dir=out_dir)
    except FileNotFoundError as exc:
        print(f"report failed: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_check(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Print an install-status table for every adapter; always exit 0."""
    rows: list[tuple[str, str, str]] = []
    for name in ADAPTER_NAMES:
        instance, load_err = _load_adapter(name)
        if instance is None:
            rows.append((name, "deferred", load_err or "unavailable"))
            continue
        check_fn = getattr(instance, "install_check", None)
        if check_fn is None:
            rows.append((name, "deferred", "no install_check() method"))
            continue
        try:
            ok, msg = check_fn()
        except Exception as exc:  # noqa: BLE001 - keep going
            rows.append((name, "deferred", f"install_check raised: {exc}"))
            continue
        status = "ok" if ok else "deferred"
        rows.append((name, status, msg or ""))

    name_w = max(len("adapter"), max(len(r[0]) for r in rows))
    stat_w = max(len("status"), max(len(r[1]) for r in rows))
    header = f"{'adapter':<{name_w}}  {'status':<{stat_w}}  message"
    print(header)
    print("-" * len(header))
    for name, status, msg in rows:
        print(f"{name:<{name_w}}  {status:<{stat_w}}  {msg}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.xray_layout.bench",
        description="xray layout library benchmark harness",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="execute adapters against binaries")
    p_run.add_argument(
        "--binary",
        default=None,
        help="single binary: corpus stem or path (overrides --inputs)",
    )
    p_run.add_argument(
        "--inputs",
        default="all",
        help="comma-separated corpus stems or 'all'",
    )
    p_run.add_argument(
        "--candidates",
        default="all",
        help="comma-separated adapter names or 'all'",
    )
    p_run.add_argument(
        "--candidate",
        default=None,
        help="single adapter name (overrides --candidates)",
    )
    p_run.add_argument(
        "--entry",
        default=None,
        help="symbol name to layout (default: adapter chooses)",
    )
    p_run.add_argument(
        "--budget",
        type=int,
        default=60,
        help="per-run time budget in seconds (default: 60)",
    )
    p_run.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    p_run.set_defaults(func=cmd_run)

    p_grid = sub.add_parser("grid", help="compose side-by-side PNG grid")
    p_grid.add_argument("--binary", required=True, help="corpus stem to grid")
    p_grid.set_defaults(func=cmd_grid)

    p_report = sub.add_parser("report", help="regenerate aggregate report")
    p_report.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"benchmark output directory (default: {DEFAULT_OUT})",
    )
    p_report.set_defaults(func=cmd_report)

    p_check = sub.add_parser("check", help="probe adapter install status")
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: "Sequence[str] | None" = None) -> int:
    """CLI entry point. Returns process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
