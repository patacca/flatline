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
