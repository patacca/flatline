"""Prune the sdist to ship only what source-builders need.

Meson dist includes the full tracked repo tree. The sdist only needs the
build system files, the flatline source package, the upstream C++ sources,
and the top-level license/notice artifacts.

This script runs as a meson.add_dist_script() hook and removes everything
else, including repo-only development tooling under `tools/`.
"""

import os
import shutil

# Top-level entries to remove entirely from the sdist.
_REMOVE_TOPLEVEL = {
    ".agents",
    ".github",
    "AGENTS.md",
    "CLAUDE.md",
    "STYLEGUIDE.md",
    "notes",
    "tests",
    "tools",
}

# Subdirectories inside docs/ to remove (AI prompts, internal dev docs).
_REMOVE_DOCS_SUBDIRS = {
    "ai",
    "archived",
}

# Individual doc files to remove (dev-only, not needed for source builds).
_REMOVE_DOCS_FILES = {
    "release_review.md",
    "release_workflow.md",
}


def _remove_path(path: str) -> None:
    """Remove a file or directory tree if it exists."""
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.isfile(path) or os.path.islink(path):
        os.remove(path)


def prune(dist_root: str) -> None:
    # --- Top-level removals ---
    for entry in _REMOVE_TOPLEVEL:
        _remove_path(os.path.join(dist_root, entry))

    # --- docs/ selective pruning ---
    docs_dir = os.path.join(dist_root, "docs")
    if os.path.isdir(docs_dir):
        for subdir in _REMOVE_DOCS_SUBDIRS:
            _remove_path(os.path.join(docs_dir, subdir))
        for filename in _REMOVE_DOCS_FILES:
            _remove_path(os.path.join(docs_dir, filename))

    # --- third_party/ghidra: keep only decompiler C++ and license files ---
    ghidra_root = os.path.join(dist_root, "third_party", "ghidra")
    if os.path.isdir(ghidra_root):
        _prune_ghidra(ghidra_root)

    # --- third_party/ogdf: keep only layered subset + license ---
    ogdf_root = os.path.join(dist_root, "third_party", "ogdf")
    if os.path.isdir(ogdf_root):
        _prune_ogdf(ogdf_root)

    # --- third_party/libavoid_src: keep only cola/libavoid + readme ---
    libavoid_root = os.path.join(dist_root, "third_party", "libavoid_src")
    if os.path.isdir(libavoid_root):
        _prune_libavoid(libavoid_root)


def _prune_ogdf(ogdf_root: str) -> None:
    """Keep only include/, src/ogdf/{basic,cluster,layered,packing}/, LICENSE.txt, README.md."""
    for entry in os.listdir(ogdf_root):
        path = os.path.join(ogdf_root, entry)
        if entry in ("LICENSE.txt", "README.md"):
            continue
        if entry == "include":
            continue
        if entry == "src":
            _prune_ogdf_src(path)
            continue
        _remove_path(path)


def _prune_ogdf_src(src_dir: str) -> None:
    """Inside src/, keep only ogdf/{basic,cluster,layered,packing}."""
    ogdf_dir = os.path.join(src_dir, "ogdf")
    if not os.path.isdir(ogdf_dir):
        return
    for entry in os.listdir(src_dir):
        entry_path = os.path.join(src_dir, entry)
        if entry == "ogdf":
            continue
        _remove_path(entry_path)
    for entry in os.listdir(ogdf_dir):
        entry_path = os.path.join(ogdf_dir, entry)
        if entry in ("basic", "cluster", "layered", "packing"):
            continue
        _remove_path(entry_path)


def _prune_libavoid(libavoid_root: str) -> None:
    """Keep only cola/libavoid/ and README.md."""
    for entry in os.listdir(libavoid_root):
        path = os.path.join(libavoid_root, entry)
        if entry == "README.md":
            continue
        if entry == "cola":
            _prune_libavoid_cola(path)
            continue
        _remove_path(path)


def _prune_libavoid_cola(cola_dir: str) -> None:
    """Inside cola/, keep only libavoid/."""
    for entry in os.listdir(cola_dir):
        entry_path = os.path.join(cola_dir, entry)
        if entry == "libavoid":
            continue
        _remove_path(entry_path)


def _prune_ghidra(ghidra_root: str) -> None:
    """Keep only LICENSE, NOTICE, and the decompiler C++ source tree."""
    for entry in os.listdir(ghidra_root):
        path = os.path.join(ghidra_root, entry)
        if entry in ("LICENSE", "NOTICE"):
            continue
        if entry == "Ghidra":
            _prune_ghidra_subdir(path)
            continue
        _remove_path(path)


def _prune_ghidra_subdir(ghidra_dir: str) -> None:
    """Keep only Ghidra/Features/Decompiler/src/decompile/cpp, remove rest."""
    keep_chain = ["Features", "Decompiler", "src", "decompile", "cpp"]

    current = ghidra_dir
    for segment in keep_chain:
        for entry in os.listdir(current):
            entry_path = os.path.join(current, entry)
            if entry == segment:
                continue
            _remove_path(entry_path)
        current = os.path.join(current, segment)
        if not os.path.isdir(current):
            return


if __name__ == "__main__":
    prune(os.environ["MESON_DIST_ROOT"])
