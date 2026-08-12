"""Read/write job-search artifacts in GCS (inbox + applications + protocol state)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.cloud import storage

INBOX_PREFIX = "inbox/recruiter"
APPS_PREFIX = "applications"
STATE_PREFIX = "protocols/_state"


def bucket_name() -> str:
    name = os.environ.get("GCS_BUCKET", "").strip()
    if not name:
        raise RuntimeError("GCS_BUCKET environment variable is required.")
    return name


def _client() -> storage.Client:
    return storage.Client()


def _bucket():
    return _client().bucket(bucket_name())


def upload_bytes(path: str, data: bytes, content_type: str) -> str:
    blob = _bucket().blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{bucket_name()}/{path}"


def upload_text(path: str, text: str, content_type: str = "text/plain; charset=utf-8") -> str:
    return upload_bytes(path, text.encode("utf-8"), content_type)


def upload_json(path: str, payload: dict[str, Any]) -> str:
    return upload_text(path, json.dumps(payload, indent=2) + "\n", "application/json")


def download_text(path: str) -> str | None:
    blob = _bucket().blob(path)
    if not blob.exists():
        return None
    return blob.download_as_text(encoding="utf-8")


def download_bytes(path: str) -> bytes | None:
    blob = _bucket().blob(path)
    if not blob.exists():
        return None
    return blob.download_as_bytes()


def list_blobs(prefix: str) -> list[str]:
    names: list[str] = []
    for blob in _client().list_blobs(_bucket(), prefix=prefix):
        if blob.name.endswith("/"):
            continue
        names.append(blob.name)
    return names


def list_inbox_messages() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in list_blobs(f"{INBOX_PREFIX}/"):
        if not path.endswith(".json") or "/_state/" in path:
            continue
        raw = download_text(path)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        data["_gcs_path"] = path
        out.append(data)
    return out


def list_application_slugs() -> set[str]:
    slugs: set[str] = set()
    for path in list_blobs(f"{APPS_PREFIX}/"):
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "applications" and parts[1]:
            slugs.add(parts[1])
    return slugs


def save_app_meta(slug: str, meta: dict[str, Any]) -> str:
    return upload_json(f"{APPS_PREFIX}/{slug}/meta.json", meta)


def load_app_meta(slug: str) -> dict[str, Any] | None:
    raw = download_text(f"{APPS_PREFIX}/{slug}/meta.json")
    if not raw:
        return None
    return json.loads(raw)


def known_message_ids() -> set[str]:
    ids: set[str] = set()
    for slug in list_application_slugs():
        meta = load_app_meta(slug)
        if not meta:
            continue
        se = meta.get("source_email") or {}
        mid = se.get("message_id")
        if mid:
            ids.add(mid)
    state = load_processed_ids()
    ids.update(state)
    return ids


def load_processed_ids() -> set[str]:
    raw = download_text(f"{STATE_PREFIX}/processed_message_ids.json")
    if not raw:
        return set()
    data = json.loads(raw)
    return set(data.get("message_ids") or [])


def save_processed_ids(ids: set[str]) -> str:
    return upload_json(
        f"{STATE_PREFIX}/processed_message_ids.json",
        {"message_ids": sorted(ids), "updated": datetime.now(timezone.utc).isoformat()},
    )


def write_protocol_summary(summary: dict[str, Any]) -> str:
    summary = {**summary, "written_at": datetime.now(timezone.utc).isoformat()}
    return upload_json(f"{STATE_PREFIX}/latest_protocol_run.json", summary)


def upload_application_file(slug: str, filename: str, content: str | bytes, content_type: str) -> str:
    path = f"{APPS_PREFIX}/{slug}/{filename}"
    if isinstance(content, str):
        return upload_text(path, content, content_type)
    return upload_bytes(path, content, content_type)


def download_prefix_to_local(prefix: str, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for blob in _client().list_blobs(_bucket(), prefix=prefix):
        name = blob.name
        if name.endswith("/"):
            continue
        rel = name[len(prefix) :].lstrip("/")
        if not rel:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size == blob.size:
            continue
        blob.download_to_filename(str(target))
        count += 1
    return count
