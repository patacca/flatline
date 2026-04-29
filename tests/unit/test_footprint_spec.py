"""Unit tests for default-install footprint measurement."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

pytest.importorskip("flatline_dev.footprint", reason="dev-only module not shipped in wheel")
from flatline_dev.footprint import (
    NativeExtensionBreakdown,
    NativeLibraryAttribution,
    _classify_symbol,
    _parse_nm_lines,
    format_default_install_footprint,
    measure_default_install_footprint,
)


class _DistributionDouble:
    """Small importlib.metadata distribution double for payload-size tests."""

    def __init__(self, name: str, root: Path, files: list[str]) -> None:
        self.metadata = {"Name": name}
        self.files = tuple(PurePosixPath(relative_path) for relative_path in files)
        self._root = root

    def locate_file(self, relative_path: PurePosixPath) -> Path:
        return self._root / Path(relative_path)


def _write_sized_file(path: Path, size_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size_bytes)


def test_u018_default_install_footprint_uses_payload_files_only(tmp_path: Path) -> None:
    """U-018: Default-install footprint excludes `__pycache__` noise deterministically."""
    site_packages = tmp_path / "site-packages"
    runtime_data_dir = site_packages / "ghidra_sleigh" / "data"

    _write_sized_file(site_packages / "flatline" / "__init__.py", 11)
    _write_sized_file(site_packages / "flatline" / "bridge" / "core.py", 29)
    _write_sized_file(site_packages / "flatline" / "__pycache__" / "__init__.pyc", 999)
    _write_sized_file(site_packages / "flatline-0.1.0.dev0.dist-info" / "METADATA", 7)

    _write_sized_file(site_packages / "networkx" / "__init__.py", 19)
    _write_sized_file(site_packages / "networkx" / "classes" / "graph.py", 31)
    _write_sized_file(site_packages / "networkx" / "__pycache__" / "__init__.pyc", 777)
    _write_sized_file(site_packages / "networkx-3.5.dist-info" / "METADATA", 23)

    _write_sized_file(site_packages / "ghidra_sleigh" / "__init__.py", 13)
    _write_sized_file(runtime_data_dir / "processors" / "x86.sla", 100)
    _write_sized_file(runtime_data_dir / "languages" / "x86.ldefs", 20)
    _write_sized_file(site_packages / "ghidra_sleigh" / "__pycache__" / "__init__.pyc", 888)
    _write_sized_file(site_packages / "ghidra_sleigh-12.0.4.dist-info" / "METADATA", 17)

    distributions = {
        "flatline": _DistributionDouble(
            "flatline",
            site_packages,
            [
                "flatline/__init__.py",
                "flatline/bridge/core.py",
                "flatline/__pycache__/__init__.pyc",
                "flatline-0.1.0.dev0.dist-info/METADATA",
            ],
        ),
        "networkx": _DistributionDouble(
            "networkx",
            site_packages,
            [
                "networkx/__init__.py",
                "networkx/classes/graph.py",
                "networkx/__pycache__/__init__.pyc",
                "networkx-3.5.dist-info/METADATA",
            ],
        ),
        "ghidra-sleigh": _DistributionDouble(
            "ghidra-sleigh",
            site_packages,
            [
                "ghidra_sleigh/__init__.py",
                "ghidra_sleigh/data/processors/x86.sla",
                "ghidra_sleigh/data/languages/x86.ldefs",
                "ghidra_sleigh/__pycache__/__init__.pyc",
                "ghidra_sleigh-12.0.4.dist-info/METADATA",
            ],
        ),
    }

    report = measure_default_install_footprint(
        distribution_loader=lambda name: distributions[name],
        runtime_data_dir_resolver=lambda: runtime_data_dir,
        native_extension_locator=lambda: None,
    )

    assert report.flatline_distribution.size_bytes == 47
    assert report.flatline_distribution.file_count == 3
    assert report.networkx_distribution.size_bytes == 73
    assert report.networkx_distribution.file_count == 3
    assert report.ghidra_sleigh_distribution.size_bytes == 150
    assert report.ghidra_sleigh_distribution.file_count == 4
    assert report.ghidra_sleigh_runtime_data.size_bytes == 120
    assert report.ghidra_sleigh_runtime_data.file_count == 2
    assert report.combined_distribution.size_bytes == 270
    assert report.combined_distribution.file_count == 10

    rendered = format_default_install_footprint(report)
    assert "payload files only; excludes __pycache__" in rendered
    assert "270 bytes" in rendered
    assert "Runtime data share of combined footprint: 44.4%" in rendered
    assert "Native extension" not in rendered


def test_classify_symbol_attributes_namespaces_to_their_libraries() -> None:
    """Demangled symbols are routed to libavoid / ogdf by their top-level namespace."""
    assert _classify_symbol("Avoid::Router::processTransaction()") == "libavoid"
    assert _classify_symbol("vtable for Avoid::ConnRef") == "libavoid"
    assert _classify_symbol("typeinfo name for Avoid::Polygon") == "libavoid"
    assert _classify_symbol("ogdf::Graph::numberOfNodes() const") == "ogdf"
    assert _classify_symbol("vtable for ogdf::SugiyamaLayout") == "ogdf"
    assert _classify_symbol("ghidra::Funcdata::startProcessing()") is None
    assert _classify_symbol("nanobind::detail::nb_func_render") is None
    assert _classify_symbol("inflate") is None


def test_parse_nm_lines_extracts_sized_symbols_only() -> None:
    """Lines without a hex size column or with zero size are dropped."""
    raw = [
        "0000000000401000 0000000000000123 T Avoid::Router::Router()",
        "0000000000401200 0000000000000045 T ogdf::Graph::Graph()",
        "0000000000401300                  U __cxa_throw",
        "0000000000401400 0000000000000000 t empty_symbol_name",
        "                                  ",
        "not a real line",
        "0000000000401500 00000000000000ff T flatline::session::run()",
    ]
    parsed = list(_parse_nm_lines(raw))
    assert parsed == [
        (0x123, "Avoid::Router::Router()"),
        (0x45, "ogdf::Graph::Graph()"),
        (0xFF, "flatline::session::run()"),
    ]


def test_measure_includes_native_extension_breakdown_when_locator_returns_path(
    tmp_path: Path,
) -> None:
    """Symbol-attributed sizes are emitted when nm yields recognizable symbols."""
    site_packages = tmp_path / "site-packages"
    runtime_data_dir = site_packages / "ghidra_sleigh" / "data"
    _write_sized_file(site_packages / "flatline" / "__init__.py", 10)
    _write_sized_file(runtime_data_dir / "x86.sla", 100)

    extension_path = site_packages / "flatline" / "_flatline_native.so"
    extension_path.parent.mkdir(parents=True, exist_ok=True)
    extension_path.write_bytes(b"\x00" * 5_000)

    distributions = {
        "flatline": _DistributionDouble("flatline", site_packages, ["flatline/__init__.py"]),
        "networkx": _DistributionDouble("networkx", site_packages, []),
        "ghidra-sleigh": _DistributionDouble("ghidra-sleigh", site_packages, []),
    }

    fake_symbols = [
        (1_000, "Avoid::Router::route()"),
        (500, "vtable for Avoid::ConnRef"),
        (2_000, "ogdf::SugiyamaLayout::call()"),
        (700, "ghidra::Funcdata::process()"),
        (300, "nanobind::detail::nb_func_render"),
    ]

    report = measure_default_install_footprint(
        distribution_loader=lambda name: distributions[name],
        runtime_data_dir_resolver=lambda: runtime_data_dir,
        native_extension_locator=lambda: extension_path,
        native_symbol_reader=lambda _: iter(fake_symbols),
    )

    breakdown = report.native_extension_breakdown
    assert breakdown is not None
    assert breakdown.extension_path == extension_path
    assert breakdown.extension_size_bytes == 5_000
    assert breakdown.sized_symbol_total_bytes == 4_500
    libraries = {lib.library_name: lib for lib in breakdown.attributed_libraries}
    assert libraries["libavoid"] == NativeLibraryAttribution("libavoid", 1_500, 2)
    assert libraries["ogdf"] == NativeLibraryAttribution("ogdf", 2_000, 1)
    assert breakdown.unattributed_size_bytes == 5_000 - 1_500 - 2_000

    rendered = format_default_install_footprint(report)
    assert "Native extension _flatline_native.so" in rendered
    assert "libavoid symbols: 1,500 bytes" in rendered
    assert "ogdf symbols: 2,000 bytes" in rendered
    assert "other (Ghidra/nanobind/zlib + binary overhead): 1,500 bytes" in rendered


def test_measure_omits_native_breakdown_when_symbol_reader_yields_nothing(
    tmp_path: Path,
) -> None:
    """When nm returns no usable symbols the breakdown still records the file size."""
    site_packages = tmp_path / "site-packages"
    runtime_data_dir = site_packages / "ghidra_sleigh" / "data"
    _write_sized_file(site_packages / "flatline" / "__init__.py", 10)
    _write_sized_file(runtime_data_dir / "x86.sla", 50)

    extension_path = site_packages / "flatline" / "_flatline_native.pyd"
    extension_path.parent.mkdir(parents=True, exist_ok=True)
    extension_path.write_bytes(b"\x00" * 1_234)

    distributions = {
        "flatline": _DistributionDouble("flatline", site_packages, ["flatline/__init__.py"]),
        "networkx": _DistributionDouble("networkx", site_packages, []),
        "ghidra-sleigh": _DistributionDouble("ghidra-sleigh", site_packages, []),
    }

    report = measure_default_install_footprint(
        distribution_loader=lambda name: distributions[name],
        runtime_data_dir_resolver=lambda: runtime_data_dir,
        native_extension_locator=lambda: extension_path,
        native_symbol_reader=lambda _: iter(()),
    )

    breakdown = report.native_extension_breakdown
    assert isinstance(breakdown, NativeExtensionBreakdown)
    assert breakdown.extension_size_bytes == 1_234
    assert breakdown.sized_symbol_total_bytes == 0
    assert all(lib.size_bytes == 0 for lib in breakdown.attributed_libraries)
    assert breakdown.unattributed_size_bytes == 1_234
