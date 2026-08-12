"""Freelancer.com job scan phase."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from freelancer_scanner import run_freelancer_scan


def run_freelancer_scan_phase() -> dict[str, Any]:
    repo = os.environ.get("REPO_ROOT") or os.environ.get("ASSETS_DIR")
    root = Path(repo) if repo else None
    return run_freelancer_scan(repo=root)
