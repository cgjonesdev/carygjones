"""Optional LinkedIn phase via Linked API HTTP (when configured)."""

from __future__ import annotations

import os
from typing import Any

import requests

from prompts import LINKEDIN_SEARCH_TERM


def run_linkedin_search(*, limit: int = 5) -> dict[str, Any]:
    token = os.environ.get("LINKED_API_TOKEN", "").strip()
    ident = os.environ.get("LINKED_IDENTIFICATION_TOKEN", "").strip()
    base = os.environ.get("LINKED_API_BASE", "https://api.linkedapi.io").rstrip("/")

    if not token or not ident:
        return {
            "phase": "linkedin",
            "skipped": True,
            "reason": "Set LINKED_API_TOKEN and LINKED_IDENTIFICATION_TOKEN secrets to enable.",
        }

    headers = {
        "linked-api-token": token,
        "identification-token": ident,
        "Content-Type": "application/json",
    }
    payload = {
        "term": LINKEDIN_SEARCH_TERM,
        "limit": limit,
        "filter": {
            "location": "Los Angeles, California",
            "datePosted": "pastWeek",
            "experienceLevels": ["midSeniorLevel"],
            "workplaceTypes": ["remote", "hybrid"],
        },
    }

    try:
        resp = requests.post(
            f"{base}/v1/jobs/search",
            headers=headers,
            json=payload,
            timeout=120,
        )
        if resp.status_code >= 400:
            return {
                "phase": "linkedin",
                "skipped": True,
                "reason": f"Linked API HTTP {resp.status_code}: {resp.text[:500]}",
            }
        data = resp.json()
        jobs = data if isinstance(data, list) else data.get("jobs") or data.get("results") or []
        return {"phase": "linkedin", "jobs_found": len(jobs), "jobs": jobs[:limit]}
    except Exception as exc:
        return {"phase": "linkedin", "skipped": True, "reason": str(exc)}
