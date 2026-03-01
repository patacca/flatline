"""Runtime-data helpers for language/compiler enumeration.

Provides deterministic runtime-data directory validation and language/compiler
pair discovery from `.ldefs` XML files. This module is internal and feeds the
bridge session startup and enumeration path.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

from flatline._errors import InternalError
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


def enumerate_runtime_data_language_compilers(
    runtime_data_dir: str | None,
) -> list[LanguageCompilerPair]:
    """Enumerate valid language/compiler pairs from runtime data.

    Rules:
    - `runtime_data_dir=None` returns an empty list.
    - missing/non-directory paths raise `InternalError`.
    - malformed `.ldefs` XML raises `InternalError`.
    - compiler entries with a declared backing spec path are filtered out when
      the backing spec file does not exist.
    """
    runtime_path = _validate_runtime_data_dir(runtime_data_dir)
    if runtime_path is None:
        return []

    pair_tuples: set[tuple[str, str]] = set()
    ldefs_paths = sorted(runtime_path.rglob("*.ldefs"))
    for ldefs_path in ldefs_paths:
        pair_tuples.update(_pairs_from_ldefs(ldefs_path))

    return [
        LanguageCompilerPair(language_id=language_id, compiler_spec=compiler_spec)
        for language_id, compiler_spec in sorted(pair_tuples)
    ]


def _validate_runtime_data_dir(runtime_data_dir: str | None) -> Path | None:
    if runtime_data_dir is None:
        return None
    runtime_path = Path(runtime_data_dir)
    if not runtime_path.exists():
        raise InternalError(f"runtime_data_dir does not exist: {runtime_data_dir!r}")
    if not runtime_path.is_dir():
        raise InternalError(f"runtime_data_dir is not a directory: {runtime_data_dir!r}")
    return runtime_path


def _pairs_from_ldefs(ldefs_path: Path) -> set[tuple[str, str]]:
    try:
        tree = ElementTree.parse(ldefs_path)
    except ElementTree.ParseError as exc:
        raise InternalError(f"invalid .ldefs XML file: {ldefs_path}: {exc}") from exc

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
