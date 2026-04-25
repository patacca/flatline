"""Validate a flatline-xray --layout-dump JSON file against schema v1.

Exit codes:
  0 = valid
  1 = file not found (input or schema)
  2 = validation error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "layout_golden"


def _schema_path(version: int) -> Path:
    return _SCHEMA_DIR / f"schema_v{version}.json"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(payload: object, schema: object) -> str | None:
    try:
        import jsonschema
    except ImportError:
        return "jsonschema is required to run validate_layout_json.py (pip install jsonschema)"

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if not errors:
        return None
    parts = []
    for err in errors:
        location = "/".join(str(p) for p in err.absolute_path) or "<root>"
        parts.append(f"  at {location}: {err.message}")
    return "schema validation failed:\n" + "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_layout_json",
        description="Validate a flatline-xray --layout-dump JSON file.",
    )
    parser.add_argument("path", type=Path, help="JSON file to validate.")
    parser.add_argument(
        "--schema-version",
        type=int,
        default=1,
        help="Schema version to validate against (default: 1).",
    )
    args = parser.parse_args(argv)

    if not args.path.exists():
        print(f"validate_layout_json: file not found: {args.path}", file=sys.stderr)
        return 1

    schema_path = _schema_path(args.schema_version)
    if not schema_path.exists():
        print(f"validate_layout_json: schema not found: {schema_path}", file=sys.stderr)
        return 1

    try:
        payload = _load_json(args.path)
    except json.JSONDecodeError as exc:
        print(f"validate_layout_json: invalid JSON in {args.path}: {exc}", file=sys.stderr)
        return 2

    schema = _load_json(schema_path)
    error_message = _validate(payload, schema)
    if error_message is not None:
        print(f"validate_layout_json: {error_message}", file=sys.stderr)
        return 2

    print(f"validate_layout_json: {args.path} OK (schema v{args.schema_version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
