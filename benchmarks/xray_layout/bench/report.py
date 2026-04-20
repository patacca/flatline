"""Aggregate Markdown report generator for xray_layout benchmark runs.

Scans all per-run JSON records produced by ``cli.py`` (under ``out/runs/``)
and synthesizes a single ``out/REPORT.md`` document. The report bundles:

- YAML frontmatter with provenance (timestamp, git SHA, branch, machine info).
- An executive summary table mapping each candidate to its tier and pass-rate.
- One section per benchmark binary with a per-candidate metric table and an
  optional grid PNG embed.
- A composite-score recommendation table for Tier 1 candidates.
- Caveats describing deferred or partially-failing candidates.

Run via:

    python -m benchmarks.xray_layout.bench report

Reads:  out/runs/<candidate>__<binary>__<function>.json
Writes: out/REPORT.md
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# Repo-relative anchors. report.py lives at bench/report.py, so the benchmark
# root (containing out/, schemas/, ...) is one directory up.
_BENCH_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUT = _BENCH_ROOT / "out"

# Canonical ordering shared with cli.ADAPTER_NAMES; duplicated here to avoid a
# circular import (cli imports from this module's package siblings).
CANDIDATES: list[str] = [
    "libavoid",
    "hola",
    "ogdf",
    "domus",
    "wueortho",
    "ogdf_libavoid",
]

# Binaries built by the corpus pipeline. Stems must match the ELF basenames
# produced under out/binaries/<stem>.elf; the report falls back gracefully
# if any are missing from the run set.
BINARIES: list[str] = [
    "tiny_branch",
    "small_loop",
    "medium_switch",
    "large_nested",
    "xlarge_state_machine",
]

# Metric column order; must be a subset of schemas/run.json metrics.
METRICS: list[str] = [
    "edge_crossings",
    "total_edge_length",
    "runtime_ms",
    "bend_count",
    "bbox_area",
    "bbox_aspect",
    "port_violations",
    "edge_overlaps",
    "same_instr_cluster_dist",
]

# Composite score weights (lower is better). Sums to 1.0; unspecified metrics
# contribute zero. Order is intentional and documented in the report body.
_SCORE_WEIGHTS: dict[str, float] = {
    "port_violations": 0.4,
    "edge_crossings": 0.3,
    "bend_count": 0.2,
    "same_instr_cluster_dist": 0.1,
}


def generate(out_dir: Path | None = None) -> Path:
    """Generate ``REPORT.md`` from every run JSON under ``out_dir/runs``.

    Args:
        out_dir: Override for the benchmark output root. Defaults to the
            in-tree ``benchmarks/xray_layout/out`` directory.

    Returns:
        The path to the written report.

    Raises:
        FileNotFoundError: If ``out_dir/runs`` does not exist.
    """
    out_dir = out_dir or _DEFAULT_OUT
    runs_dir = out_dir / "runs"
    renders_dir = out_dir / "renders"
    report_path = out_dir / "REPORT.md"

    if not runs_dir.is_dir():
        msg = f"runs directory not found: {runs_dir}"
        raise FileNotFoundError(msg)

    runs = _load_runs(runs_dir)
    lines: list[str] = []
    lines.extend(_render_frontmatter())
    lines.extend(["# xray Layout Library Benchmark Report", ""])
    lines.extend(_render_summary(runs))
    lines.extend(_render_per_binary(runs, renders_dir))
    lines.extend(_render_recommendations(runs))
    lines.extend(_render_caveats(runs))

    _ = report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {report_path}")
    return report_path


def _load_runs(runs_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Load + schema-validate every JSON in ``runs_dir``.

    Invalid or unparseable records are skipped with a stderr warning so the
    report still renders for partial datasets. The returned mapping is keyed
    by ``(candidate, binary)``; later files for the same key overwrite earlier
    ones, mirroring the on-disk filename collision behaviour.
    """
    from benchmarks.xray_layout.bench.schema import validate

    runs: dict[tuple[str, str], dict[str, Any]] = {}
    for json_path in sorted(runs_dir.glob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            validate(data)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(
                f"WARNING: skipping {json_path.name}: {exc}",
                file=sys.stderr,
            )
            continue
        runs[(data["candidate"], data["binary"])] = data
    return runs


def _render_frontmatter() -> list[str]:
    """Build the YAML provenance block at the top of the report."""
    machine = _machine_info()
    now = datetime.now(timezone.utc).isoformat()
    return [
        "---",
        f'generated_at: "{now}"',
        f'git_sha: "{_git("rev-parse", "--short", "HEAD")}"',
        f'branch: "{_git("rev-parse", "--abbrev-ref", "HEAD")}"',
        "machine:",
        f'  cpu: "{_yaml_escape(machine["cpu"])}"',
        f'  ram_gb: {machine["ram_gb"]}',
        f'  os: "{_yaml_escape(machine["os"])}"',
        f'  python: "{machine["python"]}"',
        'benchmark_version: "0.0.0"',
        "---",
        "",
    ]


def _git(*args: str) -> str:
    """Run ``git <args>`` and return stripped stdout, or 'unknown' on error."""
    try:
        return subprocess.check_output(
            ["git", *args],
            text=True,
            stderr=subprocess.DEVNULL,
            cwd=_BENCH_ROOT,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _machine_info() -> dict[str, Any]:
    """Best-effort machine description; mirrors cli._machine_info() shape."""
    cpu = platform.processor() or platform.machine() or "unknown"
    # Linux exposes a richer model string in /proc/cpuinfo; prefer it when
    # available because platform.processor() is empty on many distros.
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8")
        for line in cpuinfo.splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass

    ram_gb: float = 0.0
    try:
        import os

        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        ram_gb = round((pages * page_size) / (1024**3), 2)
    except (AttributeError, ValueError, OSError):
        pass

    return {
        "cpu": cpu,
        "ram_gb": ram_gb,
        "os": platform.platform(),
        "python": platform.python_version(),
    }


def _yaml_escape(value: str) -> str:
    """Escape double quotes and backslashes for inclusion in a YAML string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _render_summary(runs: dict[tuple[str, str], dict[str, Any]]) -> list[str]:
    """Executive summary: one row per candidate with tier and pass-rate."""
    lines = ["## Executive Summary", ""]
    lines.append("| Candidate | Tier | Binaries OK |")
    lines.append("|---|---|---|")
    for cand in CANDIDATES:
        ok_count = sum(
            1
            for b in BINARIES
            if runs.get((cand, b), {}).get("status") == "ok"
        )
        # Total = binaries with any record (deferred counts as attempted).
        total = sum(1 for b in BINARIES if (cand, b) in runs)
        tier = _tier_for(cand, runs)
        lines.append(f"| {cand} | {tier} | {ok_count}/{total} |")
    lines.append("")
    # Pointer to hand-written investigation notes (research-branch artefact).
    # Lives beside REPORT.md so it survives `bench report` regenerations.
    lines.append(
        "> See [`DOMUS_INVESTIGATION.md`](DOMUS_INVESTIGATION.md) for the "
        "DOMUS adapter/extractor fix journey and viability analysis."
    )
    lines.append("")
    return lines


def _tier_for(cand: str, runs: dict[tuple[str, str], dict[str, Any]]) -> str:
    """Classify a candidate as Tier 1 or Deferred from its run statuses."""
    statuses = [runs.get((cand, b), {}).get("status") for b in BINARIES]
    # Deferred when every status is None or 'deferred' (no real attempt ran).
    if all(s is None or s == "deferred" for s in statuses):
        return "Deferred"
    return "Tier 1"


def _render_per_binary(
    runs: dict[tuple[str, str], dict[str, Any]],
    renders_dir: Path,
) -> list[str]:
    """One table per binary, ordered by runtime_ms (ok rows first)."""
    lines = ["## Results by Binary", ""]
    for binary in BINARIES:
        lines.extend([f"### {binary}", ""])
        header = "| Candidate | Status | " + " | ".join(METRICS) + " |"
        sep = "|---|---|" + "|".join(["---"] * len(METRICS)) + "|"
        lines.extend([header, sep])

        # Sort: ok rows by runtime asc, non-ok rows last.
        rows = [(cand, runs.get((cand, binary))) for cand in CANDIDATES]
        rows.sort(key=lambda r: _sort_key(r[1]))

        for cand, run in rows:
            lines.append(_format_row(cand, run))
        lines.append("")

        # Embed the side-by-side grid render if present; otherwise leave a
        # placeholder so reviewers know the asset is missing, not forgotten.
        grid_path = renders_dir / f"{binary}__GRID.png"
        if grid_path.exists():
            lines.append(f"![{binary} grid](renders/{binary}__GRID.png)")
        else:
            lines.append(f"*Grid not available for {binary}*")
        lines.append("")
    return lines


def _sort_key(run: dict[str, Any] | None) -> tuple[int, float]:
    """Sort 'ok' runs by runtime_ms; everything else falls to the bottom."""
    if run is None or run.get("status") != "ok":
        return (1, 0.0)
    runtime = run.get("metrics", {}).get("runtime_ms", float("inf"))
    return (0, float(runtime))


def _format_row(cand: str, run: dict[str, Any] | None) -> str:
    """Render one Markdown table row for (candidate, run)."""
    if run is None:
        cells = ["-"] * len(METRICS)
        return f"| {cand} | missing | " + " | ".join(cells) + " |"
    status = run.get("status", "?")
    if status != "ok":
        cells = ["-"] * len(METRICS)
        return f"| {cand} | {status} | " + " | ".join(cells) + " |"
    metrics = run.get("metrics", {})
    cells = [_fmt(metrics.get(k)) for k in METRICS]
    return f"| {cand} | ok | " + " | ".join(cells) + " |"


def _fmt(value: Any) -> str:
    """Format a metric cell: floats to 1 decimal, ints as-is, None as '-'."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        # bool is an int subclass; render explicitly so True doesn't become 1.
        return str(value)
    if isinstance(value, float):
        return f"{value:.1f}"
    if isinstance(value, int):
        return str(value)
    return str(value)


def _render_recommendations(
    runs: dict[tuple[str, str], dict[str, Any]],
) -> list[str]:
    """Composite-score ranking over Tier 1 candidates with at least one ok."""
    weight_blurb = " + ".join(
        f"{w} * {k}" for k, w in _SCORE_WEIGHTS.items()
    )
    lines = [
        "## Recommendations",
        "",
        (
            f"Composite score = {weight_blurb} (lower is better, averaged "
            "across all 'ok' binaries; Tier 1 candidates with at least one "
            "successful run only)."
        ),
        "",
    ]

    scored: list[tuple[str, float]] = []
    for cand in CANDIDATES:
        ok_runs = [
            runs[(cand, b)]
            for b in BINARIES
            if runs.get((cand, b), {}).get("status") == "ok"
        ]
        if not ok_runs:
            continue
        score = _composite_score(ok_runs)
        scored.append((cand, score))

    if not scored:
        lines.append("*No Tier 1 candidate produced an ok run; ranking skipped.*")
        lines.append("")
        return lines

    scored.sort(key=lambda x: x[1])
    lines.append("| Candidate | Composite Score |")
    lines.append("|---|---|")
    for cand, score in scored:
        lines.append(f"| {cand} | {score:.2f} |")
    lines.append("")
    return lines


def _composite_score(ok_runs: list[dict[str, Any]]) -> float:
    """Weighted-average of selected metrics across all ok runs."""
    score = 0.0
    for key, weight in _SCORE_WEIGHTS.items():
        # Mean over runs that report this metric; missing values contribute 0.
        values = [
            float(r["metrics"][key])
            for r in ok_runs
            if key in r.get("metrics", {})
        ]
        if not values:
            continue
        score += weight * (sum(values) / len(values))
    return score


def _render_caveats(
    runs: dict[tuple[str, str], dict[str, Any]],
) -> list[str]:
    """Bullet list summarising deferred and partially-failing candidates."""
    lines = ["## Caveats", ""]
    for cand in CANDIDATES:
        cand_runs = [runs.get((cand, b)) for b in BINARIES]
        statuses = [r["status"] for r in cand_runs if r is not None]

        if not statuses:
            # Nothing on disk -> assume the adapter never ran (pre-merge or
            # not selected). Surface it so reviewers know coverage gaps.
            lines.append(
                f"- **{cand}**: NO DATA - adapter not yet executed against the corpus."
            )
            continue

        if all(s == "deferred" for s in statuses):
            # First non-empty error_message wins; falls back to a generic
            # pointer at the install notes if every record was silent.
            msgs = [
                r.get("error_message", "")
                for r in cand_runs
                if r is not None and r.get("error_message")
            ]
            detail = msgs[0] if msgs else "see adapter install notes"
            lines.append(f"- **{cand}**: DEFERRED - {detail}")
            continue

        bad_statuses = {"error", "crashed", "timeout"}
        bad_count = sum(1 for s in statuses if s in bad_statuses)
        if bad_count:
            lines.append(
                f"- **{cand}**: {bad_count}/{len(statuses)} binaries failed "
                "(error/crashed/timeout); see individual run JSONs in out/runs/."
            )
    lines.append("")
    return lines
