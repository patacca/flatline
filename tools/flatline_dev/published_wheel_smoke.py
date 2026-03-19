"""Install flatline from a package index and smoke-test the published wheel."""

from __future__ import annotations

import argparse
import importlib
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "fx_add_elf64.hex"
EXPECTED_NORMALIZED_C = (
    "int4 func_1000 ( int4 param_1 , int4 param_2 ) { return param_1 + param_2 ; }"
)
_C_TOKEN_PATTERN = re.compile(
    r"0x[0-9a-fA-F]+|"
    r"[A-Za-z_][A-Za-z0-9_]*|"
    r"\d+|"
    r"==|!=|<=|>=|->|<<|>>|&&|\|\||"
    r"[{}()\[\];,:+\-*/%<>=&|^~!]"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install flatline from PyPI/TestPyPI and run a published-wheel smoke test.",
    )
    parser.add_argument(
        "--repository",
        choices=("pypi", "testpypi"),
        required=True,
        help="Package index to install flatline from.",
    )
    parser.add_argument(
        "--install-attempts",
        type=int,
        default=12,
        help="Maximum installation attempts while waiting for index availability.",
    )
    parser.add_argument(
        "--install-wait-seconds",
        type=int,
        default=20,
        help="Seconds to wait between failed installation attempts.",
    )
    return parser.parse_args()


def _load_expected_version() -> str:
    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    return pyproject["project"]["version"]


def _load_memory_image() -> bytes:
    raw_hex = FIXTURE_PATH.read_text(encoding="ascii")
    return bytes.fromhex("".join(raw_hex.split()))


def _normalize_c_code(source: str) -> str:
    return " ".join(_C_TOKEN_PATTERN.findall(source))


def _install_command(expected_version: str, repository: str) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--force-reinstall",
        "--no-cache-dir",
        "--only-binary=:all:",
    ]
    if repository == "testpypi":
        command.extend(
            [
                "--index-url",
                "https://test.pypi.org/simple",
                "--extra-index-url",
                "https://pypi.org/simple",
            ]
        )
    command.append(f"flatline=={expected_version}")
    return command


def _install_published_wheel(
    expected_version: str, repository: str, attempts: int, wait: int
) -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        check=True,
    )

    command = _install_command(expected_version, repository)
    last_error = ""
    for attempt in range(1, attempts + 1):
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return

        last_error = completed.stderr.strip() or completed.stdout.strip()
        if attempt == attempts:
            break
        print(
            f"install attempt {attempt}/{attempts} failed; waiting {wait}s for {repository}",
            file=sys.stderr,
        )
        time.sleep(wait)

    raise RuntimeError(
        f"could not install flatline=={expected_version} from {repository}: {last_error}"
    )


def _run_smoke(expected_version: str) -> None:
    importlib.invalidate_caches()

    import ghidra_sleigh

    import flatline
    from flatline import DecompileRequest

    installed_flatline = Path(flatline.__file__).resolve()
    if REPO_ROOT in installed_flatline.parents:
        raise RuntimeError(
            f"flatline imported from repo checkout instead of site-packages: {installed_flatline}"
        )

    if flatline.__version__ != expected_version:
        raise RuntimeError(
            f"flatline.__version__={flatline.__version__!r} did not match {expected_version!r}"
        )

    runtime_data_dir = Path(ghidra_sleigh.get_runtime_data_dir())
    if not runtime_data_dir.is_dir():
        raise RuntimeError(f"ghidra_sleigh runtime data dir was not found: {runtime_data_dir}")

    request = DecompileRequest(
        memory_image=_load_memory_image(),
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
    )
    result = flatline.decompile_function(request)

    if result.error is not None:
        raise RuntimeError(f"published-wheel smoke failed with structured error: {result.error}")
    if result.c_code is None or result.function_info is None:
        raise RuntimeError("published-wheel smoke did not produce decompile output")
    if _normalize_c_code(result.c_code) != EXPECTED_NORMALIZED_C:
        raise RuntimeError("published-wheel smoke produced unexpected normalized C output")
    if result.metadata.get("language_id") != request.language_id:
        raise RuntimeError("published-wheel smoke reported unexpected language_id metadata")
    if result.metadata.get("compiler_spec") != request.compiler_spec:
        raise RuntimeError("published-wheel smoke reported unexpected compiler_spec metadata")


def main() -> int:
    args = _parse_args()
    expected_version = _load_expected_version()
    _install_published_wheel(
        expected_version,
        args.repository,
        args.install_attempts,
        args.install_wait_seconds,
    )
    _run_smoke(expected_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
