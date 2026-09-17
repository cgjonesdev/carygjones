#!/usr/bin/env python3
"""Pull recruiter inbox JSON and/or applications from GCS into the local repo."""

from __future__ import annotations

import argparse
import os
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


def _import_meta_merge():
    scripts = repo_root() / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from app_meta_merge import merge_meta_files

    return merge_meta_files


def _sync_meta_json(blob, target: Path, *, push_local_meta: bool) -> tuple[int, int]:
    """Merge remote meta.json with local; optionally push merged meta back to GCS."""
    merge_meta_files = _import_meta_merge()
    remote_text = blob.download_as_text(encoding="utf-8")
    local_text = target.read_text(encoding="utf-8") if target.exists() else None
    merged_text, push = merge_meta_files(local_text, remote_text)

    changed = (not target.exists()) or (target.read_text(encoding="utf-8") != merged_text)
    if changed:
        target.write_text(merged_text, encoding="utf-8")

    pushed = 0
    if push and push_local_meta:
        blob.upload_from_string(merged_text, content_type="application/json; charset=utf-8")
        pushed = 1

    return (1 if changed else 0, pushed)


def download_applications_prefix(dest: Path) -> tuple[int, int]:
    """Download gs://{bucket}/applications/ into local applications/.

    meta.json files are merged with local copies so interview status and Zoom links
    are not clobbered by stale GCS data. When local wins, merged meta is pushed back.
    """
    from google.cloud import storage

    prefix = "applications/"
    client = storage.Client()
    bucket = client.bucket(bucket_name())
    dest.mkdir(parents=True, exist_ok=True)
    push_local_meta = os.environ.get("GCS_PUSH_LOCAL_META", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    count = 0
    pushed = 0
    for blob in client.list_blobs(bucket, prefix=prefix):
        name = blob.name
        if name.endswith("/"):
            continue
        rel = name[len(prefix) :]
        if not rel:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)

        if rel.endswith("meta.json"):
            file_count, push_count = _sync_meta_json(
                blob, target, push_local_meta=push_local_meta
            )
            count += file_count
            pushed += push_count
            continue

        if target.exists() and target.stat().st_size == blob.size:
            continue
        blob.download_to_filename(str(target))
        count += 1
    return count, pushed


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
            apps_count, meta_pushed = download_applications_prefix(args.apps_dest)
        except Exception as exc:
            print(exc, file=sys.stderr)
            return 1
        print(
            f"Downloaded/updated {apps_count} file(s) from "
            f"gs://{bucket_name()}/applications/ → {args.apps_dest}"
        )
        if meta_pushed:
            print(f"Pushed {meta_pushed} merged meta.json file(s) back to GCS (local interview state preserved)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
