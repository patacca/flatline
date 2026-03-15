"""Repo-only wrapper for the release-readiness CLI."""

from __future__ import annotations

from flatline_dev.release import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
