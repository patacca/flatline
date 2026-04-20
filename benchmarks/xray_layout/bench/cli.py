"""Command-line interface for the xray layout benchmark.

Subcommands:
    run     -- execute one or more adapters against one or more binaries.
    grid    -- compose a side-by-side PNG grid from per-adapter renders.
    report  -- regenerate the aggregate Markdown report (stub).
    check   -- probe each adapter's install_check() and print status.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
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
    "ogdf_libavoid",
    "sugiyama_libavoid",
    "ogdf_planarization",
]

# Repo-relative anchors. The benchmark lives at benchmarks/xray_layout/, so
# we walk up three parents from this file: cli.py -> bench -> xray_layout.
BENCH_ROOT = Path(__file__).resolve().parent
XRAY_LAYOUT_ROOT = BENCH_ROOT.parent
DEFAULT_OUT = XRAY_LAYOUT_ROOT / "out"
CORPUS_DIR = XRAY_LAYOUT_ROOT / "corpus"
# Built ELFs (with paired .meta.json) live alongside DEFAULT_OUT.
# Adapter run() reads ``binary_path.read_bytes()`` and pairs the meta via
# ``binary_path.with_suffix('.meta.json')``, so stem resolution must point
# at the built ELF -- not the source .c -- for both the bytes and the meta
# to be found.
BINARIES_DIR = DEFAULT_OUT / "binaries"
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

    Accepts either a corpus stem or an absolute/relative filesystem path.
    Stems resolve to the built ELF under ``out/binaries/<stem>.elf`` because
    the adapter run loop reads the file as raw bytes and locates the meta
    via ``<binary_path>.meta.json``; the source ``.c`` does not satisfy
    either contract. Source-stem fallback is kept as a last-resort hint so
    a missing build produces a clearer downstream error than a bare miss.
    """
    p = Path(binary)
    if p.exists():
        return p.resolve()
    elf = BINARIES_DIR / f"{binary}.elf"
    if elf.exists():
        return elf.resolve()
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


def _run_one_inproc(
    adapter_name: str,
    binary_stem: str,
    binary_path: Path,
    entry: str | None,
    budget: int,
    out_dir: Path,
) -> dict[str, Any]:
    """In-process execution of a single (adapter, binary) pair.

    Invoked inside the per-case worker subprocess; never call directly from
    the harness because a hung native call (libavoid, OGDF) cannot be
    interrupted from Python and would freeze the whole benchmark suite.
    The parent ``_run_one`` enforces the wall-clock cap by killing this
    process group on timeout.
    """
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

    try:
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
    except MemoryError as exc:
        record["status"] = "crashed"
        record["error_message"] = f"OOM: {exc}"
    except Exception as exc:  # noqa: BLE001 - harness must not abort
        record["status"] = "error"
        record["error_message"] = f"{type(exc).__name__}: {exc}"
        try:
            (out_dir / "errors").mkdir(parents=True, exist_ok=True)
            (out_dir / "errors" / f"{adapter_name}__{binary_stem}.txt").write_text(
                traceback.format_exc()
            )
        except OSError:
            pass
    return record


def _run_one(
    adapter_name: str,
    binary_stem: str,
    binary_path: Path,
    entry: str | None,
    budget: int,
    out_dir: Path,
) -> dict[str, Any]:
    """Execute a single (adapter, binary) pair under a hard wall-clock cap.

    Spawns the in-process worker as a child Python process inside a fresh
    POSIX session/process group. On ``--budget`` expiry the parent sends
    SIGKILL to the entire group, which reliably stops native C++ calls
    (libavoid, OGDF, cppyy) that ignore Python-level SIGALRM. Without
    this isolation the harness silently hangs past the budget when a
    native layout call refuses to return -- the failure mode that
    motivated this design.

    A successful child writes its run record JSON to a fresh temp path
    that the parent then loads. Timeout/crash records are synthesized in
    the parent so the harness always emits exactly one record per case.
    """
    base_record: dict[str, Any] = {
        "candidate": adapter_name,
        "binary": binary_stem,
        "function": entry or "<auto>",
        "machine": _machine_info(),
    }

    fd, tmp_result_str = tempfile.mkstemp(
        prefix=f"runcase_{adapter_name}_{binary_stem}_",
        suffix=".json",
        dir=str(out_dir),
    )
    os.close(fd)
    tmp_result = Path(tmp_result_str)
    try:
        cmd = [
            sys.executable,
            "-m",
            "benchmarks.xray_layout.bench",
            "_run-case",
            "--adapter",
            adapter_name,
            "--binary-stem",
            binary_stem,
            "--binary-path",
            str(binary_path),
            "--budget",
            str(budget),
            "--out",
            str(out_dir),
            "--result-path",
            str(tmp_result),
        ]
        if entry is not None:
            cmd.extend(["--entry", entry])

        # start_new_session=True puts the child in its own process group so
        # killpg reaches grandchildren too (e.g. DOMUS's external binary).
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
            text=True,
        )

        try:
            _stderr = proc.communicate(timeout=budget)[1]
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            try:
                _stderr = proc.communicate(timeout=10)[1]
            except subprocess.TimeoutExpired:
                proc.kill()
                _stderr = ""
            record = dict(base_record)
            record["status"] = "timeout"
            record["error_message"] = (
                f"hard wall-clock timeout after {budget}s; killed worker process group"
            )
            _write_worker_stderr(out_dir, adapter_name, binary_stem, _stderr)
            return record

        if tmp_result.exists() and tmp_result.stat().st_size > 0:
            try:
                return json.loads(tmp_result.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                record = dict(base_record)
                record["status"] = "error"
                record["error_message"] = (
                    f"worker wrote unparseable result JSON: {exc}"
                )
                _write_worker_stderr(out_dir, adapter_name, binary_stem, _stderr)
                return record

        # No result file: child died before writing. Distinguish signal
        # death (rc < 0 on POSIX) from a clean non-zero exit.
        record = dict(base_record)
        if rc is not None and rc < 0:
            record["status"] = "crashed"
            record["error_message"] = (
                f"worker killed by signal {-rc} before writing result"
            )
        else:
            record["status"] = "error"
            record["error_message"] = (
                f"worker exited (code={rc}) without writing result"
            )
        _write_worker_stderr(out_dir, adapter_name, binary_stem, _stderr)
        return record
    finally:
        with contextlib.suppress(OSError):
            tmp_result.unlink(missing_ok=True)


def _write_worker_stderr(
    out_dir: Path, adapter_name: str, binary_stem: str, stderr: str | None
) -> None:
    """Persist worker stderr to out/errors/ for post-mortem inspection."""
    if not stderr:
        return
    try:
        errors_dir = out_dir / "errors"
        errors_dir.mkdir(parents=True, exist_ok=True)
        (errors_dir / f"{adapter_name}__{binary_stem}.txt").write_text(stderr)
    except OSError:
        pass


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


def cmd_run_case(args: argparse.Namespace) -> int:
    """Hidden subcommand: execute one (adapter, binary) pair in-process.

    Invoked by ``_run_one`` as a child process so the parent can enforce a
    hard wall-clock cap via ``killpg`` on its session group. Writes the
    resulting record JSON to ``--result-path`` (atomic-ish: parent creates
    a fresh empty temp file, child overwrites it). Always returns 0 on
    successful write -- the record's ``status`` field carries semantic
    success/failure -- so a non-zero exit code unambiguously means the
    worker itself crashed before recording anything.
    """
    record = _run_one_inproc(
        adapter_name=args.adapter,
        binary_stem=args.binary_stem,
        binary_path=Path(args.binary_path),
        entry=args.entry or None,
        budget=args.budget,
        out_dir=Path(args.out),
    )
    Path(args.result_path).write_text(json.dumps(record), encoding="utf-8")
    return 0


def cmd_check(args: argparse.Namespace) -> int:  # noqa: ARG001
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
        default=300,
        help="per-run time budget in seconds (default: 300)",
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

    # Hidden internal subcommand: per-case worker spawned by _run_one().
    # Not advertised in --help because it is a process-isolation
    # implementation detail of the run subcommand.
    p_runcase = sub.add_parser("_run-case", help=argparse.SUPPRESS)
    p_runcase.add_argument("--adapter", required=True)
    p_runcase.add_argument("--binary-stem", required=True)
    p_runcase.add_argument("--binary-path", required=True)
    p_runcase.add_argument("--entry", default=None)
    p_runcase.add_argument("--budget", type=int, required=True)
    p_runcase.add_argument("--out", required=True)
    p_runcase.add_argument("--result-path", required=True)
    p_runcase.set_defaults(func=cmd_run_case)

    return parser


def main(argv: "Sequence[str] | None" = None) -> int:
    """CLI entry point. Returns process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
