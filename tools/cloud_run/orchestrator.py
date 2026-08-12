"""Shared protocol orchestration for CLI job and HTTP service."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable

from gcs_apps import write_protocol_summary
from phases.craigslist_scan import run_craigslist_scan_phase
from phases.freelancer_scan import run_freelancer_scan_phase
from phases.indeed_scan import run_indeed_scan_phase
from phases.gmail_scan import run_gmail_scan
from phases.linkedin import run_linkedin_search
from phases.triage_generate import run_triage_generate


PhaseFn = Callable[[], dict[str, Any]]


def _max_generate() -> int:
    return int(os.environ.get("MAX_GENERATE_PER_RUN", "5"))


def run_gmail() -> dict[str, Any]:
    return run_gmail_scan()


def run_generate() -> dict[str, Any]:
    return run_triage_generate(max_jobs=_max_generate())


def run_linkedin() -> dict[str, Any]:
    return run_linkedin_search()


def run_freelancer() -> dict[str, Any]:
    return run_freelancer_scan_phase()


def run_craigslist() -> dict[str, Any]:
    return run_craigslist_scan_phase()


def run_indeed() -> dict[str, Any]:
    return run_indeed_scan_phase()


def run_phases(
    phases: list[tuple[str, PhaseFn]],
    *,
    mode: str = "sequential",
) -> dict[str, Any]:
    """Run selected phases sequentially or in parallel."""
    summary: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "phases": [],
    }

    if mode == "parallel":
        with ThreadPoolExecutor(max_workers=len(phases)) as pool:
            futures = {pool.submit(fn): name for name, fn in phases}
            results: dict[str, dict[str, Any]] = {}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as exc:
                    results[name] = {"phase": name, "error": str(exc)}
        for name, _fn in phases:
            summary["phases"].append(results.get(name, {"phase": name, "error": "missing result"}))
    else:
        for name, fn in phases:
            try:
                summary["phases"].append(fn())
            except Exception as exc:
                summary["phases"].append({"phase": name, "error": str(exc)})

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    uri = write_protocol_summary(summary)
    summary["summary_uri"] = uri
    return summary


def run_all(*, parallel: bool = False) -> dict[str, Any]:
    phases: list[tuple[str, PhaseFn]] = [
        ("gmail_scan", run_gmail),
        ("triage_generate", run_generate),
        ("linkedin", run_linkedin),
    ]
    skip_gmail = os.environ.get("SKIP_GMAIL_SCAN", "").lower() in ("1", "true", "yes")
    skip_generate = os.environ.get("SKIP_GENERATE", "").lower() in ("1", "true", "yes")
    skip_linkedin = os.environ.get("SKIP_LINKEDIN", "").lower() in ("1", "true", "yes")
    skip_freelancer = os.environ.get("SKIP_FREELANCER_SCAN", "1").lower() in ("1", "true", "yes")
    skip_craigslist = os.environ.get("SKIP_CRAIGSLIST_SCAN", "1").lower() in ("1", "true", "yes")
    skip_indeed = os.environ.get("SKIP_INDEED_SCAN", "1").lower() in ("1", "true", "yes")

    filtered: list[tuple[str, PhaseFn]] = []
    skipped: list[dict[str, Any]] = []
    for name, fn in phases:
        if name == "gmail_scan" and skip_gmail:
            skipped.append({"phase": name, "skipped": True})
        elif name == "triage_generate" and skip_generate:
            skipped.append({"phase": name, "skipped": True})
        elif name == "linkedin" and skip_linkedin:
            skipped.append({"phase": name, "skipped": True})
        elif name == "freelancer_scan" and skip_freelancer:
            skipped.append({"phase": name, "skipped": True, "reason": "SKIP_FREELANCER_SCAN=1"})
        elif name == "craigslist_scan" and skip_craigslist:
            skipped.append({"phase": name, "skipped": True, "reason": "SKIP_CRAIGSLIST_SCAN=1"})
        elif name == "indeed_scan" and skip_indeed:
            skipped.append({"phase": name, "skipped": True, "reason": "SKIP_INDEED_SCAN=1"})
        else:
            filtered.append((name, fn))

    if not skip_freelancer:
        filtered.append(("freelancer_scan", run_freelancer))
    if not skip_craigslist:
        filtered.append(("craigslist_scan", run_craigslist))
    if not skip_indeed:
        filtered.append(("indeed_scan", run_indeed))

    mode = "parallel" if parallel else "sequential"
    summary = run_phases(filtered, mode=mode)
    if skipped:
        summary["phases"] = skipped + summary["phases"]
    return summary
