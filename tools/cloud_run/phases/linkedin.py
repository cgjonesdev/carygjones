"""Optional LinkedIn phase via Linked API workflows (when configured)."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

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


def _start_search_workflow(*, term: str, limit: int) -> dict[str, Any]:
    payload = {
        "actionType": "st.searchJobs",
        "term": term,
        "limit": limit,
        "filter": DEFAULT_FILTERS,
    }
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
                raise RuntimeError(err.get("message") or "LinkedIn search action failed")
            jobs = completion.get("data") or []
            if not isinstance(jobs, list):
                jobs = []
            return {
                "workflowId": workflow_id,
                "message": last_message,
                "jobs": jobs,
            }

        if status == "failed":
            failure = result.get("failure") or {}
            raise RuntimeError(failure.get("message") or failure.get("reason") or "Workflow failed")

        raise RuntimeError(f"Unexpected workflow status: {status}")

    raise TimeoutError(
        f"Linked API workflow timed out after {_poll_timeout()}s"
        + (f" (last: {last_message})" if last_message else "")
    )


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
    }


def run_linkedin_search(*, limit: int = 5) -> dict[str, Any]:
    if not _credentials_ok():
        return {
            "phase": "linkedin",
            "skipped": True,
            "reason": "Set LINKED_API_TOKEN and LINKED_IDENTIFICATION_TOKEN secrets to enable.",
        }

    try:
        started = _start_search_workflow(term=LINKEDIN_SEARCH_TERM, limit=limit)
        polled = _poll_workflow(started["workflowId"])
        jobs = [_normalize_job(j) for j in polled.get("jobs", []) if isinstance(j, dict)]
        return {
            "phase": "linkedin",
            "jobs_found": len(jobs),
            "jobs": jobs[:limit],
            "workflowId": started["workflowId"],
            "queue_message": started.get("message"),
            "completion_message": polled.get("message"),
        }
    except TimeoutError as exc:
        return {"phase": "linkedin", "skipped": True, "reason": str(exc)}
    except Exception as exc:
        return {"phase": "linkedin", "skipped": True, "reason": str(exc)}
