"""Native-runtime unit tests for the bridge/decompile pipeline."""

from __future__ import annotations

import pytest

from tests._native_fixtures import (
    assert_successful_result,
    get_native_fixture,
    open_native_session,
)

pytestmark = pytest.mark.requires_native


def test_u011_native_bridge_produces_real_decompile_result(native_runtime_data_dir: str) -> None:
    """U-011: The native bridge decompiles a real function, not a skeleton response."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        pairs = session.list_language_compilers()
        if not pairs:
            pytest.skip("native language/compiler enumeration returned no pairs")
        assert (fixture.language_id, fixture.compiler_spec) in {
            (pair.language_id, pair.compiler_spec) for pair in pairs
        }
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert result.c_code.strip() != ""
    assert "not implemented" not in result.c_code.lower()
    assert result.function_info.entry_address == fixture.function_address


def test_u031_memory_load_image_skeleton_repeats_custom_tail_padding() -> None:
    """U-031: Native load-image helper repeats custom tail padding as needed."""
    native_module = pytest.importorskip("flatline._flatline_native")

    loader = native_module.MemoryLoadImageSkeleton(
        0x1000,
        b"\xaa\xbb",
        b"\x10\x20\x30",
    )
    assert loader.read(0x1001, 6) == b"\xbb\x10\x20\x30\x10\x20"

    strict_loader = native_module.MemoryLoadImageSkeleton(0x1000, b"\xaa\xbb", b"")
    with pytest.raises(ValueError, match="outside memory_image"):
        strict_loader.read(0x1001, 6)
