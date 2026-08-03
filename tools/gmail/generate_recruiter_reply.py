#!/usr/bin/env python3
"""Write applications/{slug}/reply_email.txt for a recruiter response."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from reply_generator import write_reply_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Application folder name under applications/")
    parser.add_argument(
        "--inbox-json",
        type=Path,
        help="Optional inbox/recruiter/*.json to thread subject and greeting",
    )
    args = parser.parse_args()

    try:
        path = write_reply_file(args.slug, inbox_json=args.inbox_json)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
