"""Regression tests for triage/generate meta merge helpers."""

from __future__ import annotations

from freezegun import freeze_time

from phases.generate_slug import _merge_generated_meta
from phases.triage_generate import _extract_apply_url, _merge_meta


def test_extract_apply_url_greenhouse():
    body = "Apply here: https://boards.greenhouse.io/acme/jobs/12345 thanks"
    assert _extract_apply_url(body) == "https://boards.greenhouse.io/acme/jobs/12345"


def test_extract_apply_url_ashby():
    body = "Link: https://jobs.ashbyhq.com/acme/abc-123."
    assert _extract_apply_url(body) == "https://jobs.ashbyhq.com/acme/abc-123"


def test_extract_apply_url_ignores_unrelated():
    body = "Visit https://example.com/careers for info"
    assert _extract_apply_url(body) is None


@freeze_time("2026-08-12")
def test_merge_meta_from_triage():
    generated = {
        "meta_json": {
            "company": "Weave",
            "role": "Senior Backend Engineer",
            "styling_notes": "Teal theme",
        }
    }
    score_data = {
        "company": "Weave",
        "role": "Senior Backend Engineer",
        "location": "Remote",
        "match_score": 84,
        "slug": "weave",
    }
    msg = {
        "message_id": "abc",
        "thread_id": "abc",
        "subject": "Weave role",
        "sender": "Jane <jane@weave.com>",
    }
    meta = _merge_meta(generated, score_data, msg, "https://jobs.ashbyhq.com/weave/1")
    assert meta["company"] == "Weave"
    assert meta["match_score"] == 84
    assert meta["apply_url"] == "https://jobs.ashbyhq.com/weave/1"
    assert meta["source_email"]["message_id"] == "abc"
    assert meta["_slug_hint"] == "weave"
    assert meta["created"] == "2026-08-12"


@freeze_time("2026-08-12")
def test_merge_generated_meta_preserves_existing_and_stamps():
    existing = {
        "status": "ready",
        "notes": "Prior note",
        "apply_url": "https://apply.example.com",
    }
    generated = {
        "meta_json": {
            "company": "Weave",
            "role": "Engineer",
            "location": "Remote",
            "styling_notes": "Teal",
        }
    }
    score_data = {"match_score": 90, "raw_match_score": 95}
    merged = _merge_generated_meta(existing, generated, score_data)
    assert merged["status"] == "application_in_progress"
    assert merged["match_score"] == 90
    assert merged["raw_match_score"] == 95
    assert merged["apply_url"] == "https://apply.example.com"
    assert "Generated application files on 2026-08-12" in merged["notes"]
