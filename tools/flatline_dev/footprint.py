"""Default-install footprint helpers for flatline release reviews."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from flatline.runtime import resolve_session_runtime_data_dir

_HUMAN_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMG]?)i?B?\s*$", re.IGNORECASE)
_HUMAN_SIZE_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}

_IGNORED_DISTRIBUTION_PARTS = frozenset({"__pycache__"})
_IGNORED_DISTRIBUTION_SUFFIXES = frozenset({".pyc"})


@dataclass(frozen=True)
class FootprintMeasurement:
    """One deterministic payload-footprint measurement."""

    size_bytes: int
    file_count: int

    @property
    def mebibytes(self) -> float:
        """Return the measurement in mebibytes."""
        return self.size_bytes / (1024 * 1024)


@dataclass(frozen=True)
class DefaultInstallFootprintReport:
    """Payload-footprint report for the default flatline install."""

    flatline_distribution: FootprintMeasurement
    networkx_distribution: FootprintMeasurement
    ghidra_sleigh_distribution: FootprintMeasurement
    ghidra_sleigh_runtime_data: FootprintMeasurement

    @property
    def combined_distribution(self) -> FootprintMeasurement:
        """Return the combined payload size of the default flatline install."""
        return FootprintMeasurement(
            size_bytes=(
                self.flatline_distribution.size_bytes
                + self.networkx_distribution.size_bytes
                + self.ghidra_sleigh_distribution.size_bytes
            ),
            file_count=(
                self.flatline_distribution.file_count
                + self.networkx_distribution.file_count
                + self.ghidra_sleigh_distribution.file_count
            ),
        )

    @property
    def runtime_data_share_of_combined(self) -> float:
        """Return the runtime-data share of the combined installed payload."""
        combined_size = self.combined_distribution.size_bytes
        if combined_size == 0:
            return 0.0
        return self.ghidra_sleigh_runtime_data.size_bytes / combined_size


def measure_default_install_footprint(
    *,
    distribution_loader: Callable[[str], object] = importlib_metadata.distribution,
    runtime_data_dir_resolver: Callable[[], str | Path] | None = None,
) -> DefaultInstallFootprintReport:
    """Measure the default install payload for flatline and its runtime dependencies.

    The measurement intentionally excludes interpreter-generated `__pycache__`
    entries so the reported payload stays stable across Python micro-version
    differences and focuses on shipped package contents.
    """
    if runtime_data_dir_resolver is None:
        runtime_data_dir_resolver = _default_runtime_data_dir_resolver

    flatline_distribution = _measure_distribution_payload(distribution_loader("flatline"))
    networkx_distribution = _measure_distribution_payload(distribution_loader("networkx"))
    ghidra_sleigh_distribution = _measure_distribution_payload(
        distribution_loader("ghidra-sleigh")
    )
    ghidra_sleigh_runtime_data = _measure_directory_tree(Path(runtime_data_dir_resolver()))
    return DefaultInstallFootprintReport(
        flatline_distribution=flatline_distribution,
        networkx_distribution=networkx_distribution,
        ghidra_sleigh_distribution=ghidra_sleigh_distribution,
        ghidra_sleigh_runtime_data=ghidra_sleigh_runtime_data,
    )


def format_default_install_footprint(report: DefaultInstallFootprintReport) -> str:
    """Render a human-readable default-install footprint summary."""
    combined = report.combined_distribution
    runtime_share = report.runtime_data_share_of_combined * 100
    return "\n".join(
        (
            "Default install footprint (payload files only; excludes __pycache__)",
            (f"- flatline distribution: {_format_measurement(report.flatline_distribution)}"),
            (f"- networkx distribution: {_format_measurement(report.networkx_distribution)}"),
            (
                "- ghidra-sleigh distribution: "
                f"{_format_measurement(report.ghidra_sleigh_distribution)}"
            ),
            (
                "- ghidra-sleigh runtime data: "
                f"{_format_measurement(report.ghidra_sleigh_runtime_data)}"
            ),
            f"- Combined default install: {_format_measurement(combined)}",
            f"- Runtime data share of combined footprint: {runtime_share:.1f}%",
        )
    )


def _default_runtime_data_dir_resolver() -> str:
    return resolve_session_runtime_data_dir(None)


def _measure_distribution_payload(distribution: object) -> FootprintMeasurement:
    distribution_name = _distribution_name(distribution)
    files = getattr(distribution, "files", None)
    locate_file = getattr(distribution, "locate_file", None)
    if files is None:
        raise ValueError(f"Distribution metadata does not expose a file list: {distribution_name}")
    if not callable(locate_file):
        raise TypeError(
            f"Distribution metadata does not expose locate_file(): {distribution_name}"
        )

    total_size = 0
    total_files = 0
    for relative_path in files:
        normalized_path = PurePosixPath(str(relative_path))
        if _should_skip_distribution_path(normalized_path):
            continue

        installed_path = Path(locate_file(relative_path))
        if not installed_path.is_file():
            raise FileNotFoundError(
                "Distribution file listed in metadata is missing: "
                f"{distribution_name}: {normalized_path}"
            )
        total_size += installed_path.stat().st_size
        total_files += 1

    return FootprintMeasurement(size_bytes=total_size, file_count=total_files)


def _measure_directory_tree(root: Path) -> FootprintMeasurement:
    if not root.exists():
        raise FileNotFoundError(f"Measured directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Measured path is not a directory: {root}")

    total_size = 0
    total_files = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        total_size += path.stat().st_size
        total_files += 1
    return FootprintMeasurement(size_bytes=total_size, file_count=total_files)


def _distribution_name(distribution: object) -> str:
    metadata = getattr(distribution, "metadata", None)
    if metadata is None:
        return "<unknown>"

    getter = getattr(metadata, "get", None)
    if callable(getter):
        name = getter("Name")
        if isinstance(name, str) and name:
            return name

    return "<unknown>"


def _should_skip_distribution_path(relative_path: PurePosixPath) -> bool:
    return (
        any(part in _IGNORED_DISTRIBUTION_PARTS for part in relative_path.parts)
        or relative_path.suffix in _IGNORED_DISTRIBUTION_SUFFIXES
    )


def _format_measurement(measurement: FootprintMeasurement) -> str:
    return (
        f"{measurement.size_bytes:,} bytes ({measurement.mebibytes:.2f} MiB) "
        f"across {measurement.file_count} files"
    )


def _parse_human_size(value: str) -> int:
    match = _HUMAN_SIZE_RE.match(value)
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid size format: {value!r}. Expected forms like 80M, 1G, 512K."
        )
    amount = float(match.group(1))
    unit = match.group(2).upper()
    multiplier = _HUMAN_SIZE_UNITS.get(unit, 0)
    if multiplier == 0:
        raise argparse.ArgumentTypeError(f"Invalid size unit: {unit!r}. Expected K, M, or G.")
    result = int(amount * multiplier)
    if result < 0:
        raise argparse.ArgumentTypeError(f"Size must be non-negative: {value!r}")
    return result


def _format_bytes(size_bytes: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TiB"


def _check_wheel_sizes(max_size_bytes: int) -> int:
    dist_dir = Path("dist")
    wheels = sorted(dist_dir.glob("*.whl"))
    if not wheels:
        print("Warning: no wheels found in dist/; skipping wheel size check.", file=sys.stderr)
        return 0

    failures = []
    for wheel in wheels:
        size = wheel.stat().st_size
        if size > max_size_bytes:
            failures.append(
                f"  {wheel.name}: {_format_bytes(size)} (cap: {_format_bytes(max_size_bytes)})"
            )

    if failures:
        print("Wheel size check FAILED:", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1

    print(f"All {len(wheels)} wheel(s) within size cap ({_format_bytes(max_size_bytes)}).")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the default-install footprint report as a small CLI."""
    parser = argparse.ArgumentParser(
        prog="python tools/footprint.py",
        description="Measure the default-install payload footprint for flatline.",
    )
    parser.add_argument(
        "--max-wheel-size",
        type=_parse_human_size,
        metavar="SIZE",
        help=(
            "Maximum allowed wheel size in bytes (e.g. 80M, 1G, 512K). "
            "Checks all dist/*.whl files. Exits 0 if no wheels are found."
        ),
    )
    args = parser.parse_args(argv)

    print(format_default_install_footprint(measure_default_install_footprint()))

    if args.max_wheel_size is not None:
        return _check_wheel_sizes(args.max_wheel_size)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
