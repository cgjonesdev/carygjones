"""Regression tests for Gmail draft reply helpers."""

from __future__ import annotations

from draft_reply import apply_url_from_source, reply_to_address


def test_apply_url_from_source_apply_now():
    source = {"body_text": "Apply now: https://jobs.ashbyhq.com/acme/123"}
    assert apply_url_from_source(source) == "https://jobs.ashbyhq.com/acme/123"


def test_apply_url_from_source_view_job():
    source = {"body_text": "View job: https://www.linkedin.com/jobs/view/123/"}
    assert "linkedin.com/jobs/view/123" in apply_url_from_source(source)


def test_apply_url_from_source_empty():
    assert apply_url_from_source(None) == ""


def test_reply_to_address_prefers_meta_recruiter():
    meta = {"recruiter_email": "jane@acme.com"}
    assert reply_to_address(None, meta) == "jane@acme.com"


def test_reply_to_address_skips_noreply_meta():
    meta = {"recruiter_email": "no-reply@ashbyhq.com"}
    source = {"sender": "Jane <jane@acme.com>"}
    assert reply_to_address(source, meta) == "jane@acme.com"


def test_reply_to_address_from_notes():
    meta = {"notes": "Recruiter: Jane <jane@example.com>"}
    assert reply_to_address(None, meta) == "jane@example.com"
