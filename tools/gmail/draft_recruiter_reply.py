#!/usr/bin/env python3
"""Create a Gmail draft reply to a recruiter with resume and cover letter attached."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from auth import get_gmail_service, SCOPES_COMPOSE
from draft_reply import draft_application, repo_root
from reply_generator import write_reply_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Application folder name under applications/")
    parser.add_argument(
        "--inbox-json",
        type=Path,
        help="Optional inbox/recruiter/*.json for threading and recipient",
    )
    parser.add_argument(
        "--message-id",
        help="Gmail message id to reply in-thread (overrides inbox json / meta)",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate reply_email.txt before creating the draft",
    )
    parser.add_argument(
        "--to",
        help="Override recipient when source is noreply/Indeed (e.g. recruiter@company.com)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Create draft even if meta.json already has gmail_draft_id",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send immediately instead of saving a draft (default: draft only)",
    )
    args = parser.parse_args()

    root = repo_root()
    app_dir = root / "applications" / args.slug
    if not app_dir.is_dir():
        print(f"Application not found: {app_dir}", file=sys.stderr)
        return 1

    if args.regenerate:
        write_reply_file(args.slug, inbox_json=args.inbox_json)

    service = get_gmail_service(scopes=SCOPES_COMPOSE)
    result = draft_application(
        service,
        args.slug,
        to_override=args.to or "",
        inbox_json=args.inbox_json,
        message_id_override=args.message_id or "",
        regenerate=False,
        send=args.send,
        force=args.force,
        statuses=frozenset({"ready", "applied", "interview", "rejected", "offer", "skipped", "demo"}),
        root=root,
    )

    if result.outcome == "skipped":
        print(result.detail, file=sys.stderr)
        return 1

    if result.outcome == "error":
        print(result.detail, file=sys.stderr)
        return 1

    action = "Sent" if result.outcome == "sent" else "Draft created"
    if result.outcome == "sent":
        print(f"{action}: message id {result.message_id or result.draft_id}")
    else:
        print(f"{action}: draft id {result.draft_id}")
        print("Open Gmail drafts to review before sending.")
    print(f"To: {result.to_addr}")
    print(f"Subject: {result.subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
