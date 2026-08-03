"""Persist recruiter scan payloads to Google Cloud Storage."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from google.cloud import storage

PREFIX = "inbox/recruiter"


def bucket_name() -> str:
    name = os.environ.get("GCS_BUCKET", "").strip()
    if not name:
        raise RuntimeError("GCS_BUCKET environment variable is required in cloud mode.")
    return name


def _client() -> storage.Client:
    return storage.Client()


def object_path(filename: str) -> str:
    return f"{PREFIX}/{filename}"


def list_message_ids() -> set[str]:
    client = _client()
    bucket = client.bucket(bucket_name())
    ids: set[str] = set()
    for blob in client.list_blobs(bucket, prefix=f"{PREFIX}/"):
        name = blob.name.rsplit("/", 1)[-1]
        if not name.endswith(".json") or name.startswith("_"):
            continue
        parts = name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].endswith(".json"):
            ids.add(parts[1][:-5])
    return ids


def upload_json(filename: str, payload: dict[str, Any]) -> str:
    client = _client()
    bucket = client.bucket(bucket_name())
    path = object_path(filename)
    blob = bucket.blob(path)
    blob.upload_from_string(
        json.dumps(payload, indent=2),
        content_type="application/json",
    )
    return f"gs://{bucket_name()}/{path}"


def write_run_summary(summary: dict[str, Any]) -> str:
    summary = {
        **summary,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    return upload_json("_state/latest_run.json", summary)


def download_prefix(local_dir: os.PathLike[str]) -> int:
    """Download all recruiter JSON blobs into a local directory."""
    from pathlib import Path

    dest = Path(local_dir)
    dest.mkdir(parents=True, exist_ok=True)
    client = _client()
    bucket = client.bucket(bucket_name())
    count = 0
    for blob in client.list_blobs(bucket, prefix=f"{PREFIX}/"):
        name = blob.name.rsplit("/", 1)[-1]
        if not name.endswith(".json"):
            continue
        target = dest / name
        if target.exists() and target.stat().st_size == blob.size:
            continue
        blob.download_to_filename(str(target))
        count += 1
    return count
