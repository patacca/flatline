"""Repo-only wrapper for the built-artifact audit CLI."""

from __future__ import annotations

from flatline_dev.artifacts import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
