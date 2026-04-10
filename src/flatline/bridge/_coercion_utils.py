"""Shared coercion validators for bridge payload decoding."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from flatline._errors import InternalError


def require_mapping(raw_value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(raw_value, Mapping):
        raise InternalError(f"{field_name} must be a mapping")
    return raw_value


def require_str(raw_value: Any, field_name: str) -> str:
    if not isinstance(raw_value, str):
        raise InternalError(f"{field_name} must be a string")
    return raw_value


def require_int(raw_value: Any, field_name: str) -> int:
    if not isinstance(raw_value, int) or isinstance(raw_value, bool):
        raise InternalError(f"{field_name} must be an integer")
    return raw_value


def require_optional_int(raw_value: Any, field_name: str) -> int | None:
    return None if raw_value is None else require_int(raw_value, field_name)


def require_optional_str(raw_value: Any, field_name: str) -> str | None:
    return None if raw_value is None else require_str(raw_value, field_name)


def require_bool(raw_value: Any, field_name: str) -> bool:
    if not isinstance(raw_value, bool):
        raise InternalError(f"{field_name} must be a bool")
    return raw_value


def is_sequence_like(raw_value: Any) -> bool:
    return isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes, bytearray))
