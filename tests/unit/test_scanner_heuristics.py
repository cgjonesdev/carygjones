"""Regression tests for Gmail recruiter scan heuristics."""

from __future__ import annotations

from scanner import _extract_jd_excerpt, _header, _parse_date, _score_message


def test_score_message_recruiter_signals():
    score, signals = _score_message(
        subject="Senior Python Engineer opportunity",
        sender="Jane Recruiter <jane@recruiting.com>",
        body="Job description\n" + ("Requirements: Python\n" * 50),
    )
    assert score >= 5
    assert "recruiter_sender" in signals
    assert any(s.startswith("jd_keywords") for s in signals)


def test_score_message_low_signal():
    score, signals = _score_message(
        subject="Hello",
        sender="friend@gmail.com",
        body="Short note",
    )
    assert score < 3
    assert signals == []


def test_extract_jd_excerpt_finds_job_description():
    body = "Preamble\n\nJob description\nRole details here\nMore details"
    excerpt = _extract_jd_excerpt(body, limit=500)
    assert "Job description" in excerpt or "Role details" in excerpt


def test_header_lookup():
    headers = [{"name": "Subject", "value": "Hello"}, {"name": "From", "value": "a@b.com"}]
    assert _header(headers, "subject") == "Hello"
    assert _header(headers, "missing") == ""


def test_parse_date_iso():
    iso = _parse_date("Wed, 12 Aug 2026 16:00:00 +0000")
    assert "2026" in iso
