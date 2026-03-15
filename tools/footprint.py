"""Repo-only wrapper for the footprint CLI."""

from __future__ import annotations

from flatline_dev.footprint import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
