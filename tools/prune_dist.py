"""Prune the sdist to keep only the minimal third_party/ghidra subset.

Meson dist includes the full ghidra submodule (~744 MB on disk).  The build
only needs the decompiler C++ sources and the upstream license/notice files.
This script runs as a meson.add_dist_script() hook and removes everything
else, shrinking the sdist from ~75 MB to ~4 MB.
"""

import os
import shutil
import sys

GHIDRA_KEEP = {
    "LICENSE",
    "NOTICE",
    "Ghidra/Features/Decompiler/src/decompile/cpp",
}


def prune(dist_root: str) -> None:
    ghidra_root = os.path.join(dist_root, "third_party", "ghidra")
    if not os.path.isdir(ghidra_root):
        return

    for entry in os.listdir(ghidra_root):
        path = os.path.join(ghidra_root, entry)
        if entry in ("LICENSE", "NOTICE"):
            continue
        if entry == "Ghidra":
            _prune_ghidra_subdir(os.path.join(ghidra_root, "Ghidra"))
            continue
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def _prune_ghidra_subdir(ghidra_dir: str) -> None:
    """Keep only Ghidra/Features/Decompiler/src/decompile/cpp, remove rest."""
    keep_chain = ["Features", "Decompiler", "src", "decompile", "cpp"]

    current = ghidra_dir
    for segment in keep_chain:
        for entry in os.listdir(current):
            entry_path = os.path.join(current, entry)
            if entry == segment:
                continue
            if os.path.isdir(entry_path):
                shutil.rmtree(entry_path)
            else:
                os.remove(entry_path)
        current = os.path.join(current, segment)
        if not os.path.isdir(current):
            return


if __name__ == "__main__":
    prune(os.environ["MESON_DIST_ROOT"])
