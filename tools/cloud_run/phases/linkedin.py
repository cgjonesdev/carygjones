"""Optional LinkedIn phase via Linked API workflows (when configured)."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

from phases.linkedin_applied import (
    is_applied_signal,
    linkedin_job_open_url,
    list_tracked_jobs_to_check,
    should_check_tracked_jobs,
    sync_applied_status,
    tracked_jobs_limit,
)
from prompts import LINKEDIN_SEARCH_TERM

DEFAULT_FILTERS = {
    "location": "Los Angeles, California",
    "datePosted": "pastWeek",
    "experienceLevels": ["midSeniorLevel"],
    "workplaceTypes": ["remote", "hybrid"],
}


def _headers() -> dict[str, str]:
    token = os.environ.get("LINKED_API_TOKEN", "").strip()
    ident = os.environ.get("LINKED_IDENTIFICATION_TOKEN", "").strip()
    return {
        "linked-api-token": token,
        "identification-token": ident,
        "Content-Type": "application/json",
    }


def _credentials_ok() -> bool:
    return bool(os.environ.get("LINKED_API_TOKEN", "").strip()) and bool(
        os.environ.get("LINKED_IDENTIFICATION_TOKEN", "").strip()
    )


def _api_base() -> str:
    return os.environ.get("LINKED_API_BASE", "https://api.linkedapi.io").rstrip("/")


def _poll_timeout() -> int:
    return int(os.environ.get("LINKED_API_POLL_TIMEOUT", "300"))


def _poll_interval() -> int:
    return int(os.environ.get("LINKED_API_POLL_INTERVAL", "5"))


def _start_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(
        f"{_api_base()}/workflows",
        headers=_headers(),
        json=payload,
        timeout=60,
    )
    data = resp.json()
    if resp.status_code >= 400 or not data.get("success"):
        err = data.get("error") or {}
        msg = err.get("message") or resp.text[:500]
        raise RuntimeError(f"Linked API start failed ({resp.status_code}): {msg}")
    result = data.get("result") or {}
    workflow_id = result.get("workflowId")
    if not workflow_id:
        raise RuntimeError("Linked API did not return workflowId")
    return {
        "workflowId": workflow_id,
        "workflowStatus": result.get("workflowStatus"),
        "message": result.get("message"),
    }


def _poll_workflow(workflow_id: str) -> dict[str, Any]:
    deadline = time.time() + _poll_timeout()
    last_message = ""
    while time.time() < deadline:
        resp = requests.get(
            f"{_api_base()}/workflows/{workflow_id}",
            headers=_headers(),
            timeout=60,
        )
        data = resp.json()
        if resp.status_code >= 400 or not data.get("success"):
            err = data.get("error") or {}
            msg = err.get("message") or resp.text[:500]
            raise RuntimeError(f"Linked API poll failed ({resp.status_code}): {msg}")

        result = data.get("result") or {}
        status = result.get("workflowStatus")
        last_message = result.get("message") or last_message

        if status in ("pending", "running"):
            time.sleep(_poll_interval())
            continue

        if status == "completed":
            completion = result.get("completion") or {}
            if not completion.get("success"):
                err = completion.get("error") or {}
                raise RuntimeError(err.get("message") or "LinkedIn workflow action failed")
            return {
                "workflowId": workflow_id,
                "message": last_message,
                "completion": completion,
            }

        if status == "failed":
            failure = result.get("failure") or {}
            raise RuntimeError(failure.get("message") or failure.get("reason") or "Workflow failed")

        raise RuntimeError(f"Unexpected workflow status: {status}")

    raise TimeoutError(
        f"Linked API workflow timed out after {_poll_timeout()}s"
        + (f" (last: {last_message})" if last_message else "")
    )


def _completion_jobs(completion: dict[str, Any]) -> list[dict[str, Any]]:
    data = completion.get("data")
    if isinstance(data, list):
        return [j for j in data if isinstance(j, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _run_search_jobs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    started = _start_workflow(payload)
    polled = _poll_workflow(started["workflowId"])
    return _completion_jobs(polled.get("completion") or {})


def _run_open_job(job_url: str) -> dict[str, Any]:
    normalized = linkedin_job_open_url(None, job_url) or job_url.strip()
    started = _start_workflow(
        {
            "actionType": "st.openJob",
            "jobUrl": normalized,
            "basicInfo": True,
        }
    )
    polled = _poll_workflow(started["workflowId"])
    jobs = _completion_jobs(polled.get("completion") or {})
    return jobs[0] if jobs else {}


def _check_tracked_jobs_applied() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {"checked": 0, "applied_found": 0, "errors": []}
    if not should_check_tracked_jobs():
        return [], meta

    applied_jobs: list[dict[str, Any]] = []
    for row in list_tracked_jobs_to_check()[: tracked_jobs_limit()]:
        try:
            data = _run_open_job(row["job_url"])
            meta["checked"] += 1
            if is_applied_signal(data):
                meta["applied_found"] += 1
                applied_jobs.append(
                    {
                        "jobId": row["job_id"],
                        "jobUrl": row["job_url"],
                        "applied": True,
                        "slug": row["slug"],
                    }
                )
        except Exception as exc:
            meta["errors"].append(f"{row['slug']}: {exc}")
    return applied_jobs, meta


def _normalize_job(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "jobId": raw.get("jobId"),
        "title": raw.get("title"),
        "company": raw.get("companyName") or raw.get("company"),
        "location": raw.get("location"),
        "workplaceType": raw.get("workplaceType"),
        "easyApply": raw.get("easyApply"),
        "apply_url": raw.get("jobUrl") or raw.get("applyUrl"),
        "salary": raw.get("salary"),
        "linkedin_applied": raw.get("applied") if "applied" in raw else None,
    }


def run_linkedin_search(*, limit: int = 5) -> dict[str, Any]:
    if not _credentials_ok():
        return {
            "phase": "linkedin",
            "skipped": True,
            "reason": "Set LINKED_API_TOKEN and LINKED_IDENTIFICATION_TOKEN secrets to enable.",
        }

    try:
        search_raw = _run_search_jobs(
            {
                "actionType": "st.searchJobs",
                "term": LINKEDIN_SEARCH_TERM,
                "limit": limit,
                "filter": DEFAULT_FILTERS,
            }
        )
        tracked_raw, tracked_meta = _check_tracked_jobs_applied()
        sync_result = sync_applied_status(
            search_jobs=search_raw,
            applied_jobs=tracked_raw or None,
        )
        jobs = [_normalize_job(j) for j in search_raw]

        result: dict[str, Any] = {
            "phase": "linkedin",
            "jobs_found": len(jobs),
            "jobs": jobs[:limit],
            "applied_sync": {
                "tracked_jobs_checked": tracked_meta.get("checked", 0),
                "tracked_jobs_applied": tracked_meta.get("applied_found", 0),
                "meta_updated": sync_result.get("updated") or [],
                "already_applied": sync_result.get("already_applied", 0),
                "applied_job_ids_seen": sync_result.get("applied_job_ids_seen", 0),
            },
        }
        if tracked_meta.get("errors"):
            result["applied_sync"]["tracked_errors"] = tracked_meta["errors"]
        return result
    except TimeoutError as exc:
        return {"phase": "linkedin", "skipped": True, "reason": str(exc)}
    except Exception as exc:
        return {"phase": "linkedin", "skipped": True, "reason": str(exc)}
