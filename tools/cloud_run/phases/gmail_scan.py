"""Gmail scan phase — delegates to existing job_runner."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def run_gmail_scan() -> dict:
    app_root = Path(os.environ.get("APP_ROOT", Path(__file__).resolve().parents[2]))
    gmail_dir = app_root / "gmail"
    if not gmail_dir.is_dir() and (app_root / "tools" / "gmail").is_dir():
        gmail_dir = app_root / "tools" / "gmail"
    if str(gmail_dir) not in sys.path:
        sys.path.insert(0, str(gmail_dir))
    os.environ.setdefault("JOB_MODE", "cloud")
    import job_runner  # noqa: WPS433

    rc = job_runner.main()
    return {"exit_code": rc, "phase": "gmail_scan"}
