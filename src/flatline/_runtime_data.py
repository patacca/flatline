"""Runtime-data helpers for language/compiler enumeration.

Provides deterministic runtime-data directory validation and language/compiler
pair discovery from `.ldefs` XML files. This module is internal and feeds the
bridge session startup and enumeration path.
"""

from __future__ import annotations

import importlib
import warnings
from os import fspath
from pathlib import Path
from xml.etree import ElementTree

from flatline._errors import ConfigurationError
from flatline._models import LanguageCompilerPair

_LANGUAGE_TAGS: frozenset[str] = frozenset({
    "language",
    "language_description",
    "languagedescription",
})

_COMPILER_TAGS: frozenset[str] = frozenset({
    "compiler",
    "compiler_spec",
    "compilerspec",
})

_LANGUAGE_ID_ATTRS: tuple[str, ...] = (
    "id",
    "language_id",
    "languageId",
)

_COMPILER_NAME_ATTRS: tuple[str, ...] = (
    "name",
    "id",
    "compiler_spec",
    "compilerSpec",
)

_COMPILER_SPEC_PATH_ATTRS: tuple[str, ...] = (
    "spec",
    "cspec",
    "specfile",
    "compiler_spec_file",
    "compilerSpecFile",
)

_MAX_PARSE_FAILURE_PREVIEW = 5


def resolve_session_runtime_data_dir(runtime_data_dir: str | Path | None) -> str:
    """Resolve the runtime-data root for public session entry points.

    Explicit overrides are normalized and used as-is. When omitted, flatline
    auto-discovers the installed `ghidra_sleigh` package to preserve the
    one-package default UX.
    """
    if runtime_data_dir is not None:
        return fspath(runtime_data_dir)

    ghidra_sleigh = _load_runtime_data_package()
    runtime_data_getter = getattr(ghidra_sleigh, "get_runtime_data_dir", None)
    if not callable(runtime_data_getter):
        raise ConfigurationError(
            "ghidra-sleigh does not expose a callable get_runtime_data_dir(); "
            "reinstall the package or pass runtime_data_dir explicitly"
        )

    return fspath(runtime_data_getter())


def enumerate_runtime_data_language_compilers(
    runtime_data_dir: str | Path | None,
) -> list[LanguageCompilerPair]:
    """Enumerate valid language/compiler pairs from runtime data.

    Rules:
    - `runtime_data_dir=None` returns an empty list.
    - missing/non-directory paths raise `ConfigurationError`.
    - malformed `.ldefs` XML is skipped if at least one valid pair is found.
    - malformed `.ldefs` XML raises `ConfigurationError` if no valid pairs are found.
    - malformed `.ldefs` XML emits one `RuntimeWarning` when skipped.
    - compiler entries with a declared backing spec path are filtered out when
      the backing spec file does not exist.
    """
    runtime_path = _validate_runtime_data_dir(runtime_data_dir)
    if runtime_path is None:
        return []

    pair_tuples: set[tuple[str, str]] = set()
    parse_failures: list[str] = []
    ldefs_paths = sorted(runtime_path.rglob("*.ldefs"))
    for ldefs_path in ldefs_paths:
        file_pairs, parse_error = _pairs_from_ldefs_tolerant(ldefs_path)
        pair_tuples.update(file_pairs)
        if parse_error is not None:
            parse_failures.append(parse_error)

    if parse_failures and pair_tuples:
        warnings.warn(
            (
                "Skipped malformed .ldefs files while enumerating runtime data "
                f"({len(parse_failures)} file(s)): "
                f"{_format_parse_failure_summary(parse_failures)}. "
                "Returning language/compiler pairs from valid files."
            ),
            RuntimeWarning,
            stacklevel=2,
        )
    elif parse_failures and not pair_tuples:
        raise ConfigurationError(
            (
                "No valid language/compiler pairs found; malformed .ldefs files "
                f"were encountered ({len(parse_failures)} file(s)): "
                f"{_format_parse_failure_summary(parse_failures)}"
            ),
        )

    return [
        LanguageCompilerPair(language_id=language_id, compiler_spec=compiler_spec)
        for language_id, compiler_spec in sorted(pair_tuples)
    ]


def _validate_runtime_data_dir(runtime_data_dir: str | Path | None) -> Path | None:
    if runtime_data_dir is None:
        return None
    runtime_path = Path(runtime_data_dir)
    if not runtime_path.exists():
        raise ConfigurationError(
            f"runtime_data_dir does not exist: {runtime_data_dir}"
        )
    if not runtime_path.is_dir():
        raise ConfigurationError(
            f"runtime_data_dir is not a directory: {runtime_data_dir}"
        )
    return runtime_path


def _pairs_from_ldefs_tolerant(ldefs_path: Path) -> tuple[set[tuple[str, str]], str | None]:
    """Parse one `.ldefs` file with tolerant error reporting."""
    try:
        pair_tuples = _pairs_from_ldefs(ldefs_path)
    except ElementTree.ParseError as exc:
        return set(), f"invalid .ldefs XML file: {ldefs_path}: {exc}"
    return pair_tuples, None


def _pairs_from_ldefs(ldefs_path: Path) -> set[tuple[str, str]]:
    tree = ElementTree.parse(ldefs_path)

    root = tree.getroot()
    pair_tuples: set[tuple[str, str]] = set()
    for language_element in root.iter():
        if _normalized_tag(language_element.tag) not in _LANGUAGE_TAGS:
            continue
        language_id = _get_first_non_empty_attr(language_element, _LANGUAGE_ID_ATTRS)
        if language_id is None:
            continue
        pair_tuples.update(
            _compiler_pairs_for_language(
                language_element=language_element,
                language_id=language_id,
                ldefs_dir=ldefs_path.parent,
            ),
        )
    return pair_tuples


def _format_parse_failure_summary(parse_failures: list[str]) -> str:
    preview_failures = parse_failures[:_MAX_PARSE_FAILURE_PREVIEW]
    parts = list(preview_failures)
    remaining_count = len(parse_failures) - len(preview_failures)
    if remaining_count > 0:
        parts.append(f"... and {remaining_count} more")
    return "; ".join(parts)


def _compiler_pairs_for_language(
    *,
    language_element: ElementTree.Element,
    language_id: str,
    ldefs_dir: Path,
) -> set[tuple[str, str]]:
    pair_tuples: set[tuple[str, str]] = set()
    for compiler_element in language_element.iter():
        if _normalized_tag(compiler_element.tag) not in _COMPILER_TAGS:
            continue
        compiler_name = _get_first_non_empty_attr(compiler_element, _COMPILER_NAME_ATTRS)
        if compiler_name is None:
            continue

        declared_spec_path = _get_first_non_empty_attr(
            compiler_element,
            _COMPILER_SPEC_PATH_ATTRS,
        )
        if declared_spec_path is not None and not _compiler_spec_exists(
            ldefs_dir=ldefs_dir,
            declared_spec_path=declared_spec_path,
        ):
            continue

        pair_tuples.add((language_id, compiler_name))
    return pair_tuples


def _compiler_spec_exists(*, ldefs_dir: Path, declared_spec_path: str) -> bool:
    candidate = ldefs_dir / declared_spec_path
    if candidate.exists():
        return True

    spec_filename = Path(declared_spec_path).name
    if not spec_filename:
        return False

    return any(ldefs_dir.rglob(spec_filename))


def _normalized_tag(tag: str) -> str:
    if "}" in tag:
        tag = tag.rsplit("}", maxsplit=1)[-1]
    return tag.replace("-", "_").lower()


def _get_first_non_empty_attr(
    element: ElementTree.Element,
    attribute_names: tuple[str, ...],
) -> str | None:
    for attribute_name in attribute_names:
        raw_value = element.attrib.get(attribute_name)
        if raw_value is None:
            continue
        value = raw_value.strip()
        if value:
            return value
    return None


def _load_runtime_data_package() -> object:
    try:
        return importlib.import_module("ghidra_sleigh")
    except ImportError as exc:
        raise ConfigurationError(
            "flatline requires ghidra-sleigh for default runtime data; "
            "reinstall flatline or pass runtime_data_dir explicitly"
        ) from exc

