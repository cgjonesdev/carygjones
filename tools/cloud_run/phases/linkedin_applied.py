"""Match LinkedIn job IDs to GCS applications and mark status applied."""

from __future__ import annotations

import os
import re
from datetime import date
from typing import Any

import gcs_apps

JOB_ID_RE = re.compile(r"/(?:comm/)?jobs/view/(\d+)")
APPLIED_STATUS_WORDS = frozenset(
    {
        "applied",
        "submitted",
        "in_review",
        "in review",
        "viewed",
        "interview",
    }
)
APPLIED_BOOL_KEYS = (
    "applied",
    "hasApplied",
    "isApplied",
    "applicationSubmitted",
    "alreadyApplied",
)


def job_id_from_value(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if text.isdigit():
        return text
    match = JOB_ID_RE.search(text)
    return match.group(1) if match else None


def job_id_from_meta(meta: dict[str, Any]) -> str | None:
    jid = job_id_from_value(meta.get("linkedin_job_id"))
    if jid:
        return jid
    return job_id_from_value(meta.get("apply_url"))


def linkedin_job_open_url(job_id: str | None, apply_url: str | None = None) -> str:
    """Canonical job URL for Linked API (rejects /comm/jobs/view/ email links)."""
    jid = job_id_from_value(job_id) or job_id_from_value(apply_url)
    if not jid:
        return ""
    return f"https://www.linkedin.com/jobs/view/{jid}/"


def is_applied_signal(raw: dict[str, Any]) -> bool:
    if not isinstance(raw, dict):
        return False
    for key in APPLIED_BOOL_KEYS:
        if raw.get(key) is True:
            return True
    for key in ("applicationStatus", "jobApplicationStatus", "listingType", "status"):
        value = str(raw.get(key) or "").strip().lower()
        if value in APPLIED_STATUS_WORDS:
            return True
        if "applied" in value and "not" not in value:
            return True
    return False


def collect_job_ids(jobs: list[dict[str, Any]], *, assume_applied: bool = False) -> set[str]:
    ids: set[str] = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        jid = job_id_from_value(str(job.get("jobId") or "")) or job_id_from_value(
            job.get("jobUrl") or job.get("applyUrl") or job.get("apply_url")
        )
        if not jid:
            continue
        if assume_applied or is_applied_signal(job):
            ids.add(jid)

        then = job.get("then")
        if isinstance(then, dict):
            data = then.get("data")
            if isinstance(data, dict):
                nested = job_id_from_value(str(data.get("jobId") or "")) or job_id_from_value(
                    data.get("jobUrl") or data.get("applyUrl")
                )
                if nested and (assume_applied or is_applied_signal(data)):
                    ids.add(nested)
    return ids


def build_job_index() -> dict[str, str]:
    """Map LinkedIn job id -> application slug."""
    index: dict[str, str] = {}
    for slug in gcs_apps.list_application_slugs():
        meta = gcs_apps.load_app_meta(slug)
        if not meta:
            continue
        jid = job_id_from_meta(meta)
        if jid:
            index[jid] = slug
    return index


def sync_applied_status(
    *,
    search_jobs: list[dict[str, Any]] | None = None,
    applied_jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Update meta.json for applications whose LinkedIn job id is known applied."""
    applied_ids = set()
    if applied_jobs:
        applied_ids |= collect_job_ids(applied_jobs, assume_applied=True)
    if search_jobs:
        applied_ids |= collect_job_ids(search_jobs, assume_applied=False)

    index = build_job_index()
    updates: list[dict[str, Any]] = []
    skipped = 0

    for jid, slug in index.items():
        if jid not in applied_ids:
            continue
        meta = gcs_apps.load_app_meta(slug)
        if not meta:
            continue
        if meta.get("status") == "applied":
            skipped += 1
            continue

        today = date.today().isoformat()
        meta = dict(meta)
        meta["status"] = "applied"
        meta["updated"] = today
        meta.setdefault("linkedin_job_id", jid)
        note = (meta.get("notes") or "").strip()
        marker = f"LinkedIn applied detected {today}."
        if marker not in note:
            meta["notes"] = f"{note} {marker}".strip() if note else marker
        gcs_apps.save_app_meta(slug, meta)
        updates.append(
            {
                "slug": slug,
                "company": meta.get("company"),
                "job_id": jid,
                "status": "applied",
            }
        )

    return {
        "applied_job_ids_seen": len(applied_ids),
        "updated": updates,
        "already_applied": skipped,
    }


def should_check_tracked_jobs() -> bool:
    return os.environ.get("LINKEDIN_CHECK_TRACKED_JOBS", "1").lower() not in (
        "0",
        "false",
        "no",
    )


def tracked_jobs_limit() -> int:
    return int(os.environ.get("LINKEDIN_APPLIED_CHECK_LIMIT", "15"))


def list_tracked_jobs_to_check() -> list[dict[str, str]]:
    """Non-applied applications with a LinkedIn job id or apply URL."""
    rows: list[dict[str, str]] = []
    for slug in gcs_apps.list_application_slugs():
        meta = gcs_apps.load_app_meta(slug)
        if not meta or meta.get("status") == "applied":
            continue
        jid = job_id_from_meta(meta)
        if not jid:
            continue
        apply_url = (meta.get("apply_url") or "").strip()
        job_url = linkedin_job_open_url(jid, apply_url)
        if not job_url:
            continue
        rows.append({"slug": slug, "job_id": jid, "job_url": job_url})
    return rows
