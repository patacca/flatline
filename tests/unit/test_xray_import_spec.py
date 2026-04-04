"""Unit tests for the flatline.xray import and input-helper contract."""

from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path


def _purge_xray_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "flatline.xray" or module_name.startswith("flatline.xray."):
            sys.modules.pop(module_name, None)


def test_u033_flatline_xray_import_is_headless_safe(monkeypatch) -> None:
    """U-033: `flatline.xray` imports without touching tkinter."""
    _purge_xray_modules()
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tkinter":
            raise AssertionError("tkinter should not be imported during flatline.xray import")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module = importlib.import_module("flatline.xray")

    assert callable(module.main)
    assert "flatline.xray._graph_window" not in sys.modules


def test_u034_xray_request_builder_reads_temp_memory_image(tmp_path: Path) -> None:
    """U-034: X-Ray request building preserves caller-supplied file inputs."""
    xray_inputs = importlib.import_module("flatline.xray._inputs")
    memory_path = tmp_path / "image.bin"
    memory_path.write_bytes(b"\x8d\x04\x37\xc3")
    runtime_data_dir = tmp_path / "runtime-data"

    target = xray_inputs.MemoryImageTarget(
        memory_path=memory_path,
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
    )

    request = xray_inputs.build_decompile_request(
        target,
        runtime_data_dir=runtime_data_dir,
    )

    assert target.read_memory_image() == b"\x8d\x04\x37\xc3"
    assert request.memory_image == b"\x8d\x04\x37\xc3"
    assert request.base_address == 0x1000
    assert request.function_address == 0x1000
    assert request.language_id == "x86:LE:64:default"
    assert request.compiler_spec == "gcc"
    assert request.runtime_data_dir == str(runtime_data_dir)
    assert request.enriched is True
