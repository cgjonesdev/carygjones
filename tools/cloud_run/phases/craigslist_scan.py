"""Craigslist gigs scan phase."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from craigslist_scanner import run_craigslist_scan


def run_craigslist_scan_phase() -> dict[str, Any]:
    repo = os.environ.get("REPO_ROOT") or os.environ.get("ASSETS_DIR")
    root = Path(repo) if repo else None
    return run_craigslist_scan(repo=root)
