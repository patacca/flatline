"""Repo-only wrapper for the compliance audit CLI."""

from __future__ import annotations

from flatline_dev.compliance import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
