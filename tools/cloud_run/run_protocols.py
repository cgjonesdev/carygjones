"""Cloud Run job: run all job-search protocols (Gmail → OpenAI generate → optional LinkedIn)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure package imports work in container and local dev.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator import run_all  # noqa: E402


def main() -> int:
    parallel = os.environ.get("RUN_PARALLEL", "").lower() in ("1", "true", "yes")
    summary = run_all(parallel=parallel)
    print(json.dumps(summary, indent=2))
    print(f"Protocol summary: {summary.get('summary_uri')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
