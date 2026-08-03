#!/usr/bin/env python3
"""Create Gmail drafts for every pending application with a recruiter address."""

from __future__ import annotations

import argparse
import sys

from auth import get_gmail_service, SCOPES_COMPOSE
from draft_reply import DEFAULT_DRAFT_STATUSES, draft_all_pending


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create Gmail draft replies for all applications under applications/ "
            "that are ready, have PDFs, and a human recruiter address."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be drafted without calling Gmail",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print skipped applications and reasons",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate reply_email.txt before drafting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Create drafts even if meta.json already has gmail_draft_id",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send immediately instead of saving drafts (use with care)",
    )
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help=(
            "Include application status (repeatable). "
            f"Default: {', '.join(sorted(DEFAULT_DRAFT_STATUSES))}"
        ),
    )
    args = parser.parse_args()

    statuses = frozenset(args.statuses) if args.statuses else DEFAULT_DRAFT_STATUSES
    service = None if args.dry_run else get_gmail_service(scopes=SCOPES_COMPOSE)

    results = draft_all_pending(
        service,
        regenerate=args.regenerate,
        send=args.send,
        dry_run=args.dry_run,
        force=args.force,
        statuses=statuses,
    )

    created = sent = skipped = errors = 0
    for result in results:
        if result.outcome == "error":
            print(f"Error: {result.slug} — {result.detail}", file=sys.stderr)
            errors += 1
        elif result.outcome == "skipped":
            skipped += 1
            if args.verbose:
                print(f"Skipped: {result.slug} — {result.detail}")
        elif result.outcome == "sent":
            sent += 1
            print(f"Sent: {result.slug}")
            print(f"  To: {result.to_addr}")
            print(f"  Subject: {result.subject}")
            print(f"  Id: {result.draft_id}")
        elif result.outcome == "created":
            created += 1
            label = "Would draft" if args.dry_run else "Draft"
            print(f"{label}: {result.slug}")
            print(f"  To: {result.to_addr}")
            print(f"  Subject: {result.subject}")
            if result.draft_id:
                print(f"  Id: {result.draft_id}")

    print()
    if args.dry_run:
        print(f"Dry run: {created} would draft, {skipped} skipped, {errors} errors.")
    else:
        print(f"Done: {created} draft(s), {sent} sent, {skipped} skipped, {errors} errors.")
        if created:
            print("Open Gmail → Drafts to review before sending.")
    if skipped and not args.verbose:
        print("Run with --verbose to see why applications were skipped.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
