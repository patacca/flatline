"""Regenerate committed fixture `.hex` files from checked-in source snippets."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
from pathlib import Path
from string import hexdigits
from textwrap import wrap

FIXTURES_DIR = Path(__file__).resolve().parent
SOURCES_DIR = FIXTURES_DIR / "sources"


def _run(command: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        command,
        check=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _extract_text_section_hex(object_path: Path) -> bytes:
    output = _run(["readelf", "-x", ".text", str(object_path)], cwd=object_path.parent)
    parts: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.startswith("0x"):
            continue
        for field in stripped.split()[1:5]:
            if len(field) == 8 and all(char in hexdigits for char in field):
                parts.append(field)
    return bytes.fromhex("".join(parts))


def _render_hex(data: bytes) -> str:
    return "\n".join(wrap(data.hex(), 64)) + "\n"


def _check_or_write(path: Path, data: bytes, *, check: bool) -> None:
    rendered = _render_hex(data)
    if check:
        if path.read_text(encoding="ascii") != rendered:
            raise SystemExit(f"fixture mismatch: {path}")
        return
    path.write_text(rendered, encoding="ascii")


def _build_text_fixture(
    source_name: str,
    target: str,
    fixture_name: str,
    *,
    check: bool,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        object_path = tmpdir / f"{fixture_name}.o"
        _run(
            [
                "clang",
                f"--target={target}",
                "-c",
                str(SOURCES_DIR / source_name),
                "-o",
                str(object_path),
            ],
            cwd=FIXTURES_DIR,
        )
        data = _extract_text_section_hex(object_path)
    _check_or_write(FIXTURES_DIR / f"{fixture_name}.hex", data, check=check)


def _build_switch_fixture(*, check: bool) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        elf_path = tmpdir / "fx_switch_elf64.elf"
        binary_path = tmpdir / "fx_switch_elf64.bin"
        _run(
            [
                "clang",
                "-O2",
                "-fno-pic",
                "-no-pie",
                "-nostdlib",
                "-Wl,-e,switch_blocks",
                "-Wl,--build-id=none",
                "-Wl,-Ttext=0x1000",
                str(SOURCES_DIR / "fx_switch_elf64.c"),
                "-o",
                str(elf_path),
            ],
            cwd=FIXTURES_DIR,
        )
        subprocess.run(
            [
                "objcopy",
                "-O",
                "binary",
                "-j",
                ".text",
                "-j",
                ".rodata",
                str(elf_path),
                str(binary_path),
            ],
            check=True,
            cwd=FIXTURES_DIR,
        )
        data = binary_path.read_bytes()
    _check_or_write(FIXTURES_DIR / "fx_switch_elf64.hex", data, check=check)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    _build_text_fixture("fx_add_elf64.s", "x86_64-linux-gnu", "fx_add_elf64", check=args.check)
    _build_text_fixture("fx_add_elf32.s", "i386-linux-gnu", "fx_add_elf32", check=args.check)
    _build_text_fixture("fx_add_arm64.s", "aarch64-linux-gnu", "fx_add_arm64", check=args.check)
    _build_text_fixture(
        "fx_add_riscv64.s",
        "riscv64-linux-gnu",
        "fx_add_riscv64",
        check=args.check,
    )
    _build_text_fixture("fx_add_mips32.s", "mipsel-linux-gnu", "fx_add_mips32", check=args.check)
    _build_text_fixture(
        "fx_warning_elf64.s",
        "x86_64-linux-gnu",
        "fx_warning_elf64",
        check=args.check,
    )
    _build_switch_fixture(check=args.check)

    if not args.check:
        for path in sorted(FIXTURES_DIR.glob("fx_*.hex")):
            digest = hashlib.sha256(
                bytes.fromhex("".join(path.read_text(encoding="ascii").split()))
            ).hexdigest()
            print(f"{path.name}: {digest}")


if __name__ == "__main__":
    main()
