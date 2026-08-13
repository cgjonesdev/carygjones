#!/usr/bin/env python3
"""Merge local and remote application meta.json without clobbering newer local interview state."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

DONE_STATUSES = frozenset({"applied", "skipped", "rejected", "offer"})
INTERVIEW_STATUSES = frozenset(
    {
        "interview",
        "screening_interview_complete",
        "in_technical_interviews",
        "technical_interviews_complete",
        "in_final_interviews",
        "final_interviews_complete",
    }
)

# Fields preserved from local when remote is stale or missing them.
LOCAL_PRIORITY_FIELDS = (
    "status",
    "updated",
    "notes",
    "interview_notes",
    "interview_url",
    "recruiter_email",
    "recruiter_name",
    "apply_url",
    "apply_method",
    "gmail_draft_id",
    "gmail_sent_message_id",
    "salary",
    "client",
    "role",
    "location",
    "match_score",
    "source_email",
)


def application_status(meta: dict[str, Any]) -> str:
    return str(meta.get("status") or "ready").strip().lower()


def _updated_key(meta: dict[str, Any]) -> str:
    return str(meta.get("updated") or "").strip()


def _has_message_id(meta: dict[str, Any]) -> bool:
    source = meta.get("source_email")
    if not isinstance(source, dict):
        return False
    return bool(str(source.get("message_id") or "").strip())


def _interview_notes_text(meta: dict[str, Any]) -> str:
    return str(meta.get("interview_notes") or "").strip()


def merge_interview_notes(
    local: dict[str, Any],
    remote: dict[str, Any],
    merged: dict[str, Any],
) -> None:
    """Never drop non-empty interview notes from either side."""
    local_text = _interview_notes_text(local)
    remote_text = _interview_notes_text(remote)
    if not local_text and not remote_text:
        merged.pop("interview_notes", None)
        return
    if local_text and not remote_text:
        merged["interview_notes"] = local_text
        return
    if remote_text and not local_text:
        merged["interview_notes"] = remote_text
        return
    if local_text == remote_text:
        merged["interview_notes"] = local_text
        return

    local_updated = _updated_key(local)
    remote_updated = _updated_key(remote)
    if local_updated > remote_updated:
        merged["interview_notes"] = local_text
    elif remote_updated > local_updated:
        merged["interview_notes"] = remote_text
    elif len(local_text) >= len(remote_text):
        merged["interview_notes"] = local_text
    else:
        merged["interview_notes"] = remote_text


def local_should_win_over_remote(local: dict[str, Any], remote: dict[str, Any]) -> bool:
    local_updated = _updated_key(local)
    remote_updated = _updated_key(remote)
    if local_updated and remote_updated and local_updated > remote_updated:
        return True

    local_status = application_status(local)
    remote_status = application_status(remote)
    if local_status in INTERVIEW_STATUSES and remote_status in DONE_STATUSES:
        return True

    if local.get("interview_url") and not remote.get("interview_url"):
        return True

    if _has_message_id(local) and not _has_message_id(remote):
        return True

    local_notes = _interview_notes_text(local)
    remote_notes = _interview_notes_text(remote)
    if local_notes and not remote_notes and local_updated >= remote_updated:
        return True

    return False


def merge_application_meta(
    local: dict[str, Any] | None,
    remote: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Return (merged_meta, push_to_gcs).

    push_to_gcs is True when merged differs from remote and local knowledge should
    be propagated back to GCS (local was newer or protected interview state).
    """
    if not local:
        return deepcopy(remote), False

    merged = deepcopy(remote)
    local_wins = local_should_win_over_remote(local, remote)

    if local_wins:
        merged = {**remote, **local}
        merged["updated"] = max(_updated_key(local), _updated_key(remote)) or _updated_key(local)
        if application_status(local) in INTERVIEW_STATUSES:
            merged["status"] = local.get("status")
        merge_interview_notes(local, remote, merged)
        push = merged != remote
        return merged, push

    # Remote is newer or same — still backfill interview-critical fields local has.
    for field in LOCAL_PRIORITY_FIELDS:
        if field == "interview_notes":
            continue
        local_val = local.get(field)
        remote_val = merged.get(field)
        if field == "source_email":
            if isinstance(local_val, dict) and (
                not isinstance(remote_val, dict)
                or (_has_message_id(local) and not _has_message_id(remote))
            ):
                merged["source_email"] = local_val
            continue
        if local_val and not remote_val:
            merged[field] = local_val

    merge_interview_notes(local, remote, merged)
    push = merged != remote
    return merged, push


if __name__ == "__main__":
    # Quick self-check: nextera-style clobber scenario
    remote = {
        "status": "applied",
        "updated": "2026-07-31",
        "notes": "old",
    }
    local = {
        "status": "interview",
        "updated": "2026-08-12",
        "interview_url": "https://zoom.us/j/123",
        "notes": "screen today",
    }
    merged, push = merge_application_meta(local, remote)
    assert merged["status"] == "interview", merged
    assert merged["interview_url"] == "https://zoom.us/j/123", merged
    assert push is True, push

    # Stale GCS pull must not drop local interview notes.
    remote = {
        "status": "applied",
        "updated": "2026-08-12",
        "notes": "protocol updated meta",
    }
    local = {
        "status": "interview",
        "updated": "2026-08-12",
        "interview_notes": "Round 1 — asked about Django ORM",
    }
    merged, push = merge_application_meta(local, remote)
    assert merged["interview_notes"] == "Round 1 — asked about Django ORM", merged
    assert push is True, push

    # Prod notes win when GCS meta is newer.
    remote = {
        "status": "interview",
        "updated": "2026-08-13",
        "interview_notes": "Saved from Cloud Run",
    }
    local = {
        "status": "interview",
        "updated": "2026-08-12",
        "interview_notes": "Older local draft",
    }
    merged, push = merge_application_meta(local, remote)
    assert merged["interview_notes"] == "Saved from Cloud Run", merged

    print("app_meta_merge self-check ok")


def merge_meta_files(local_text: str | None, remote_text: str) -> tuple[str, bool]:
    remote = json.loads(remote_text)
    local = json.loads(local_text) if local_text else None
    merged, push = merge_application_meta(local, remote)
    return json.dumps(merged, indent=2) + "\n", push
