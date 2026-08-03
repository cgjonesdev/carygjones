#!/usr/bin/env python3
"""Pull recruiter inbox JSON from GCS into the local repo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from storage import bucket_name, download_prefix
except ImportError as exc:
    if "google.cloud" in str(exc) or "storage" in str(exc):
        print(
            "Missing Google Cloud libraries. From tools/gmail run:\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    raise


def repo_inbox_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "inbox" / "recruiter"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=repo_inbox_dir(),
        help="Local directory (default: inbox/recruiter/)",
    )
    args = parser.parse_args()

    try:
        count = download_prefix(args.dest)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Downloaded/updated {count} file(s) from gs://{bucket_name()}/inbox/recruiter/ → {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
