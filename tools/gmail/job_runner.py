#!/usr/bin/env python3
"""Cloud Run Job entrypoint: scan Gmail and persist new recruiter mail to GCS."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

from auth import get_gmail_service
from scanner import fetch_recruiter_emails, to_export_dict

DEFAULT_JOB_QUERY = os.environ.get(
    "GMAIL_QUERY",
    (
        "newer_than:7d ("
        "subject:(job OR opportunity OR position OR role OR interview OR hiring OR engineer OR developer) OR "
        "from:(recruit OR talent OR hiring OR careers OR linkedin OR indeed OR greenhouse OR lever OR tcs.com)"
        ")"
    ),
)


def re_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "message"


def main() -> int:
    max_results = int(os.environ.get("SCAN_MAX_RESULTS", "25"))
    min_score = int(os.environ.get("SCAN_MIN_SCORE", "3"))

    print(f"Starting recruiter scan at {datetime.now(timezone.utc).isoformat()}")
    print(f"Query: {DEFAULT_JOB_QUERY}")

    service = get_gmail_service()
    emails = fetch_recruiter_emails(
        service,
        query=DEFAULT_JOB_QUERY,
        max_results=max_results,
        min_score=min_score,
    )

    from storage import list_message_ids, upload_json, write_run_summary

    existing = list_message_ids()
    saved: list[dict] = []
    skipped = 0

    for email in emails:
        short_id = email.message_id[:8]
        if short_id in existing:
            skipped += 1
            continue
        slug = re_slug(email.subject or email.message_id)
        filename = f"{slug}_{short_id}.json"
        payload = to_export_dict(email)
        uri = upload_json(filename, payload)
        saved.append(
            {
                "message_id": email.message_id,
                "subject": email.subject,
                "score": email.score,
                "gcs_uri": uri,
            }
        )
        print(f"saved {uri} score={email.score} subj={email.subject!r}")

    summary = {
        "matched": len(emails),
        "saved_new": len(saved),
        "skipped_existing": skipped,
        "query": DEFAULT_JOB_QUERY,
        "new_messages": saved,
    }
    summary_uri = write_run_summary(summary)
    print(json.dumps({**summary, "summary_uri": summary_uri}, indent=2))
    print(
        f"Done: {len(saved)} new, {skipped} already in bucket, {len(emails)} total matched.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
