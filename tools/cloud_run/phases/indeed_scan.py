"""Indeed job search scan phase."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from indeed_scanner import run_indeed_scan


def run_indeed_scan_phase() -> dict[str, Any]:
    repo = os.environ.get("REPO_ROOT") or os.environ.get("ASSETS_DIR")
    root = Path(repo) if repo else None
    return run_indeed_scan(repo=root)
