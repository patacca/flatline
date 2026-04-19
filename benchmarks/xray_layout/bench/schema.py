"""JSON Schema validation for xray_layout benchmark run records.

Example valid 'ok' payload:
    {
        "candidate": "libavoid",
        "binary": "test_binary",
        "function": "main",
        "status": "ok",
        "machine": {"cpu": "x86_64", "ram_gb": 16, "os": "linux"},
        "metrics": {
            "edge_crossings": 5,
            "total_edge_length": 1234.5,
            "runtime_ms": 100.0,
            "bend_count": 10,
            "bbox_area": 5000.0,
            "bbox_aspect": 1.5,
            "port_violations": 0,
            "edge_overlaps": 2,
            "same_instr_cluster_dist": 15.0
        },
        "outputs": {"png_path": "out.png", "svg_path": "out.svg"}
    }

Example valid 'timeout' payload:
    {
        "candidate": "hola",
        "binary": "test_binary",
        "function": "foo",
        "status": "timeout",
        "machine": {"cpu": "arm64", "ram_gb": 8, "os": "macos"}
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


def _load_schema() -> dict[str, Any]:
    """Load the JSON schema from the schemas directory."""
    schema_path = Path(__file__).parent.parent / "schemas" / "run.json"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def validate(payload: dict[str, Any]) -> None:
    """Validate a benchmark run payload against the JSON schema.

    Args:
        payload: The benchmark run record to validate.

    Raises:
        ValueError: If the payload does not match the schema.
    """
    from jsonschema import Draft7Validator, ValidationError

    schema = _load_schema()
    validator = Draft7Validator(schema)

    errors = list(validator.iter_errors(payload))
    if errors:
        messages = []
        for error in errors:
            path = "/".join(str(p) for p in error.path) if error.path else "root"
            messages.append(f"[{path}] {error.message}")
        raise ValueError(f"Schema validation failed: {'; '.join(messages)}")
