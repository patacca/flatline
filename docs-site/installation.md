# Installation

## Prerequisites

- Python 3.13 or later
- pip

Pre-built wheels are available for Linux x86_64/aarch64, Windows x86_64, and
macOS x86_64/arm64. On these platforms a C++ compiler is not required.

Platforms outside that matrix fall back to a source build, which additionally
requires a C++20 compiler, Ninja, and zlib development headers.

| Platform | Native build dependencies |
|---|---|
| Ubuntu / Debian | `sudo apt-get install g++ ninja-build zlib1g-dev` |
| Fedora / RHEL | `sudo dnf install gcc-c++ ninja-build zlib-devel` |
| Arch Linux | `sudo pacman -S gcc ninja zlib` |
| macOS | `brew install ninja zlib` (Xcode provides the compiler) |
| Windows | Visual Studio with the C++ workload; `pip install ninja`; `vcpkg install zlib:x64-windows` |

## Install from PyPI

```bash
pip install flatline
```

This pulls in the `ghidra-sleigh` companion package, which ships the compiled
Sleigh processor definitions that flatline needs at runtime. No separate
download or path configuration is required.

`pip install flatline` already includes the shipped `flatline-xray` viewer.
The viewer uses Ghidra's Sleigh disassembly natively, so no extra install is
needed for decoded instructions. `tkinter` is part of the Python standard
library, but some distributions package it separately.
If `flatline-xray` reports that `tkinter` is missing, install the platform
package for your Python distribution and rerun the tool.

## Build from source

Use this path when you want to work on flatline itself, run the test suite, or
install on a platform without a pre-built wheel.

```bash
git clone https://github.com/patacca/flatline.git
cd flatline
git submodule update --init
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The editable install compiles the native C++ extension automatically if a
suitable compiler is found. To force a native build and fail loudly if
prerequisites are missing:

```bash
pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled
```

## Verify the installation

```python
import flatline

info = flatline.get_version_info()
print(info.flatline_version)    # e.g. "0.1.0"
print(info.decompiler_version)  # e.g. "ghidra-6.1"
```

!!! note
    The `decompiler_version` (e.g. `"ghidra-6.1"`) refers to the Ghidra
    **decompiler engine**, which is versioned independently from the main
    Ghidra project.  It does **not** correspond to the Ghidra application
    version (e.g. Ghidra 12.0.4).

If the native extension built correctly, `flatline.decompile_function` will
produce real decompiled output. Without the native extension the API is fully
importable but every decompile call returns a `configuration_error` result
rather than C code.

## Optional X-Ray viewer

The shipped `flatline-xray` utility uses the same request fields as the core
API: raw memory image bytes, base address, function address, and target
selection. The viewer is documented in the [X-Ray section](xray/index.md), with
a step-by-step tutorial at [X-Ray Tutorial](xray/tutorial.md).
