"""Native-runtime unit tests for the bridge/decompile pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from flatline import DecompileRequest, DecompilerSession

pytestmark = pytest.mark.requires_native


def test_u015_native_decompile_path_is_not_stub() -> None:
    """U-015: Native bridge uses a real decompile path (not the old stub response)."""
    repo_root = Path(__file__).resolve().parents[2]
    runtime_data_dir = repo_root / "third_party" / "ghidra" / "Ghidra" / "Processors"
    if not runtime_data_dir.exists():
        pytest.skip("runtime_data_dir fixture is unavailable in this checkout")

    with DecompilerSession(runtime_data_dir=str(runtime_data_dir)) as session:
        pairs = session.list_language_compilers()
        if not pairs:
            pytest.skip("native language/compiler enumeration returned no pairs")

        pair = next(
            (item for item in pairs if item.language_id == "x86:LE:64:default"),
            pairs[0],
        )
        request = DecompileRequest(
            memory_image=b"\xC3",
            base_address=0x1000,
            function_address=0x1000,
            language_id=pair.language_id,
            compiler_spec=pair.compiler_spec,
            runtime_data_dir=str(runtime_data_dir),
        )
        result = session.decompile_function(request)

    if result.error is None:
        assert result.c_code is not None
        assert result.c_code.strip() != ""
        assert result.function_info is not None
        assert result.function_info.entry_address == request.function_address
    else:
        assert result.error.category in {
            "decompile_failed",
            "invalid_address",
            "unsupported_target",
        }
        assert "not yet implemented" not in result.error.message.lower()
