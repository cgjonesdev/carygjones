#!/usr/bin/env python3
"""Scan Gmail for recruiter emails with likely job descriptions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from auth import get_gmail_service
from scanner import fetch_recruiter_emails, to_export_dict

DEFAULT_QUERY = (
    "newer_than:30d ("
    "subject:(job OR opportunity OR position OR role OR interview OR hiring OR engineer OR developer) OR "
    "from:(recruit OR talent OR hiring OR careers OR linkedin OR indeed OR greenhouse OR lever OR tcs.com)"
    ")"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "inbox" / "recruiter"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Gmail search query")
    parser.add_argument("--max", type=int, default=25, dest="max_results")
    parser.add_argument("--min-score", type=int, default=3)
    parser.add_argument(
        "--save",
        action="store_true",
        help="Write JSON files to inbox/recruiter/",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON to stdout")
    args = parser.parse_args()

    service = get_gmail_service()
    emails = fetch_recruiter_emails(
        service,
        query=args.query,
        max_results=args.max_results,
        min_score=args.min_score,
    )

    if not emails:
        print("No recruiter emails matched.", file=sys.stderr)
        return 0

    if args.save:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for email in emails:
            slug = re_slug(email.subject or email.message_id)
            path = OUT_DIR / f"{slug}_{email.message_id[:8]}.json"
            path.write_text(json.dumps(to_export_dict(email), indent=2))
            print(f"saved {path}")

    if args.json:
        print(json.dumps([to_export_dict(e) for e in emails], indent=2))
    else:
        for email in emails:
            print("-" * 72)
            print(f"score={email.score}  date={email.date}")
            print(f"from: {email.sender}")
            print(f"subj: {email.subject}")
            print(f"url:  https://mail.google.com/mail/u/0/#inbox/{email.message_id}")
            if email.jd_excerpt:
                print("\nJD excerpt:")
                print(email.jd_excerpt[:1200])
                if len(email.jd_excerpt) > 1200:
                    print("…")

    print(f"\n{len(emails)} message(s) matched.", file=sys.stderr)
    return 0


def re_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "message"


if __name__ == "__main__":
    raise SystemExit(main())
