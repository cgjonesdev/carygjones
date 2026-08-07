#!/usr/bin/env python3
"""Pull recruiter inbox JSON and/or applications from GCS into the local repo."""

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


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def repo_inbox_dir() -> Path:
    return repo_root() / "inbox" / "recruiter"


def repo_applications_dir() -> Path:
    return repo_root() / "applications"


def download_applications_prefix(dest: Path) -> int:
    """Download gs://{bucket}/applications/ into local applications/."""
    from google.cloud import storage

    prefix = "applications/"
    client = storage.Client()
    bucket = client.bucket(bucket_name())
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for blob in client.list_blobs(bucket, prefix=prefix):
        name = blob.name
        if name.endswith("/"):
            continue
        rel = name[len(prefix) :]
        if not rel:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size == blob.size:
            continue
        blob.download_to_filename(str(target))
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=repo_inbox_dir(),
        help="Local inbox directory (default: inbox/recruiter/)",
    )
    parser.add_argument(
        "--applications",
        action="store_true",
        help="Also pull gs://{bucket}/applications/ → applications/",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Pull inbox and applications (same as --applications with default inbox dest)",
    )
    parser.add_argument(
        "--apps-dest",
        type=Path,
        default=repo_applications_dir(),
        help="Local applications directory (default: applications/)",
    )
    args = parser.parse_args()

    try:
        inbox_count = download_prefix(args.dest)
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1

    print(
        f"Downloaded/updated {inbox_count} file(s) from "
        f"gs://{bucket_name()}/inbox/recruiter/ → {args.dest}"
    )

    if args.applications or args.all:
        try:
            apps_count = download_applications_prefix(args.apps_dest)
        except Exception as exc:
            print(exc, file=sys.stderr)
            return 1
        print(
            f"Downloaded/updated {apps_count} file(s) from "
            f"gs://{bucket_name()}/applications/ → {args.apps_dest}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
