"""Default-install footprint helpers for flatline release reviews."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from flatline.runtime import resolve_session_runtime_data_dir

_HUMAN_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([KMG]?)i?B?\s*$", re.IGNORECASE)
_HUMAN_SIZE_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}

_IGNORED_DISTRIBUTION_PARTS = frozenset({"__pycache__"})
_IGNORED_DISTRIBUTION_SUFFIXES = frozenset({".pyc"})

# Demangled-symbol prefixes used to attribute native-module bytes back to the
# statically-linked third-party libraries. The vendored libraries put all
# public symbols inside these top-level namespaces, so a prefix match is
# sufficient. We also catch `vtable for`, `typeinfo for`, and
# `typeinfo name for` records that nm emits for C++ classes.
_NATIVE_LIBRARY_NAMESPACES: tuple[tuple[str, str], ...] = (
    ("libavoid", "Avoid::"),
    ("ogdf", "ogdf::"),
)
_NATIVE_LIBRARY_DECORATIONS: tuple[str, ...] = (
    "",
    "vtable for ",
    "typeinfo for ",
    "typeinfo name for ",
    "construction vtable for ",
    "VTT for ",
    "guard variable for ",
)


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
class NativeLibraryAttribution:
    """Symbol-attributed byte share of one statically-linked native library."""

    library_name: str
    size_bytes: int
    symbol_count: int


@dataclass(frozen=True)
class NativeExtensionBreakdown:
    """Symbol-level attribution of a native extension's on-disk size.

    `attributed_libraries` covers libraries whose symbols carry an identifying
    namespace prefix (libavoid, ogdf). The remaining bytes -- ELF/PE/Mach-O
    overhead, read-only data, Ghidra/nanobind/zlib symbols, and anything
    nm could not size -- live in `unattributed_size_bytes`.
    """

    extension_path: Path
    extension_size_bytes: int
    attributed_libraries: tuple[NativeLibraryAttribution, ...]
    sized_symbol_total_bytes: int

    @property
    def unattributed_size_bytes(self) -> int:
        attributed = sum(lib.size_bytes for lib in self.attributed_libraries)
        return self.extension_size_bytes - attributed


@dataclass(frozen=True)
class DefaultInstallFootprintReport:
    """Payload-footprint report for the default flatline install."""

    flatline_distribution: FootprintMeasurement
    networkx_distribution: FootprintMeasurement
    ghidra_sleigh_distribution: FootprintMeasurement
    ghidra_sleigh_runtime_data: FootprintMeasurement
    native_extension_breakdown: NativeExtensionBreakdown | None = None

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
    native_extension_locator: Callable[[], Path | None] | None = None,
    native_symbol_reader: Callable[[Path], Iterable[tuple[int, str]]] | None = None,
) -> DefaultInstallFootprintReport:
    """Measure the default install payload for flatline and its runtime dependencies.

    The measurement intentionally excludes interpreter-generated `__pycache__`
    entries so the reported payload stays stable across Python micro-version
    differences and focuses on shipped package contents.

    When the native extension is installed and a working symbol reader (`nm`)
    is available, the report also includes a per-library byte attribution for
    the statically-linked native dependencies (libavoid, ogdf).
    """
    if runtime_data_dir_resolver is None:
        runtime_data_dir_resolver = _default_runtime_data_dir_resolver
    if native_extension_locator is None:
        native_extension_locator = _default_native_extension_locator
    if native_symbol_reader is None:
        native_symbol_reader = _read_native_symbols_via_nm

    flatline_distribution = _measure_distribution_payload(distribution_loader("flatline"))
    networkx_distribution = _measure_distribution_payload(distribution_loader("networkx"))
    ghidra_sleigh_distribution = _measure_distribution_payload(
        distribution_loader("ghidra-sleigh")
    )
    ghidra_sleigh_runtime_data = _measure_directory_tree(Path(runtime_data_dir_resolver()))
    native_extension_breakdown = _measure_native_extension_breakdown(
        native_extension_locator, native_symbol_reader
    )
    return DefaultInstallFootprintReport(
        flatline_distribution=flatline_distribution,
        networkx_distribution=networkx_distribution,
        ghidra_sleigh_distribution=ghidra_sleigh_distribution,
        ghidra_sleigh_runtime_data=ghidra_sleigh_runtime_data,
        native_extension_breakdown=native_extension_breakdown,
    )


def format_default_install_footprint(report: DefaultInstallFootprintReport) -> str:
    """Render a human-readable default-install footprint summary."""
    combined = report.combined_distribution
    runtime_share = report.runtime_data_share_of_combined * 100
    lines = [
        "Default install footprint (payload files only; excludes __pycache__)",
        f"- flatline distribution: {_format_measurement(report.flatline_distribution)}",
        f"- networkx distribution: {_format_measurement(report.networkx_distribution)}",
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
    ]
    if report.native_extension_breakdown is not None:
        lines.append("")
        lines.extend(_format_native_extension_breakdown(report.native_extension_breakdown))
    return "\n".join(lines)


def _format_native_extension_breakdown(breakdown: NativeExtensionBreakdown) -> list[str]:
    extension_size = breakdown.extension_size_bytes
    lines = [
        (
            f"Native extension {breakdown.extension_path.name}: "
            f"{extension_size:,} bytes ({extension_size / (1024 * 1024):.2f} MiB)"
        ),
    ]
    for lib in breakdown.attributed_libraries:
        share = (lib.size_bytes / extension_size * 100) if extension_size else 0.0
        lines.append(
            f"- {lib.library_name} symbols: {lib.size_bytes:,} bytes "
            f"({lib.size_bytes / (1024 * 1024):.2f} MiB, {share:.1f}% of extension) "
            f"across {lib.symbol_count} symbols"
        )
    unattributed = breakdown.unattributed_size_bytes
    unattributed_share = (unattributed / extension_size * 100) if extension_size else 0.0
    lines.append(
        f"- other (Ghidra/nanobind/zlib + binary overhead): {unattributed:,} bytes "
        f"({unattributed / (1024 * 1024):.2f} MiB, {unattributed_share:.1f}% of extension)"
    )
    lines.append(
        "  Note: per-library figures are lower bounds derived from sized symbols only; "
        "section padding, read-only data, and unsized symbols fall into 'other'."
    )
    return lines


def _default_runtime_data_dir_resolver() -> str:
    return resolve_session_runtime_data_dir(None)


def _default_native_extension_locator() -> Path | None:
    """Locate the installed `_flatline_native` extension on disk, if present."""
    try:
        import flatline as _flatline_pkg
    except ImportError:
        return None
    package_root = Path(_flatline_pkg.__file__).resolve().parent
    candidates = sorted(package_root.glob("_flatline_native*"))
    for candidate in candidates:
        if candidate.is_file() and candidate.suffix.lower() in {".so", ".pyd", ".dylib"}:
            return candidate
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _measure_native_extension_breakdown(
    locator: Callable[[], Path | None],
    symbol_reader: Callable[[Path], Iterable[tuple[int, str]]],
) -> NativeExtensionBreakdown | None:
    extension_path = locator()
    if extension_path is None or not extension_path.is_file():
        return None
    try:
        symbols = list(symbol_reader(extension_path))
    except FileNotFoundError, OSError, RuntimeError:
        return None

    sized_total = 0
    per_library_size: dict[str, int] = {name: 0 for name, _ in _NATIVE_LIBRARY_NAMESPACES}
    per_library_count: dict[str, int] = {name: 0 for name, _ in _NATIVE_LIBRARY_NAMESPACES}
    for size, demangled in symbols:
        sized_total += size
        library_name = _classify_symbol(demangled)
        if library_name is not None:
            per_library_size[library_name] += size
            per_library_count[library_name] += 1

    attributed = tuple(
        NativeLibraryAttribution(
            library_name=name,
            size_bytes=per_library_size[name],
            symbol_count=per_library_count[name],
        )
        for name, _ in _NATIVE_LIBRARY_NAMESPACES
    )
    return NativeExtensionBreakdown(
        extension_path=extension_path,
        extension_size_bytes=extension_path.stat().st_size,
        attributed_libraries=attributed,
        sized_symbol_total_bytes=sized_total,
    )


def _classify_symbol(demangled: str) -> str | None:
    for library_name, namespace in _NATIVE_LIBRARY_NAMESPACES:
        for decoration in _NATIVE_LIBRARY_DECORATIONS:
            if demangled.startswith(decoration + namespace):
                return library_name
    return None


def _read_native_symbols_via_nm(extension_path: Path) -> Iterable[tuple[int, str]]:
    """Yield `(size_bytes, demangled_symbol)` pairs from `nm` output.

    Returns an empty iterable on platforms where `nm` is unavailable or
    cannot parse the binary (typical on Windows, where the wheel is a `.pyd`
    built by MSVC). Callers must therefore tolerate an empty result.
    """
    nm_path = shutil.which("nm")
    if nm_path is None:
        return ()
    try:
        completed = subprocess.run(
            [nm_path, "--print-size", "--demangle", str(extension_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except OSError, subprocess.TimeoutExpired:
        return ()
    if completed.returncode != 0 or not completed.stdout:
        return ()
    return tuple(_parse_nm_lines(completed.stdout.splitlines()))


def _parse_nm_lines(lines: Iterable[str]) -> Iterable[tuple[int, str]]:
    """Parse `nm --print-size --demangle` lines into `(size, symbol)` pairs.

    Expected layout per sized symbol:
        `<address> <size_hex> <type_letter> <demangled symbol...>`
    Lines without a size column (4+ fields) are silently skipped, matching
    nm's behaviour for symbols whose size cannot be determined.
    """
    for line in lines:
        parts = line.split(maxsplit=3)
        if len(parts) < 4:
            continue
        type_letter = parts[2]
        if len(type_letter) != 1 or not type_letter.isalpha():
            continue
        try:
            size = int(parts[1], 16)
        except ValueError:
            continue
        if size <= 0:
            continue
        yield size, parts[3]


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
