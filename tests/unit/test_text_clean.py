"""Regression tests for email/JD text normalization."""

from __future__ import annotations

from text_clean import (
    clean_email_body,
    clean_jd_text,
    html_to_plain_text,
    normalize_whitespace,
    strip_email_boilerplate,
)


def test_html_to_plain_text_strips_tags_and_scripts(load_fixture):
    html = load_fixture("email", "indeed_html_snippet.html")
    plain = html_to_plain_text(html)
    assert "<" not in plain
    assert "Senior Python Engineer" in plain
    assert "color: red" not in plain


def test_normalize_whitespace_collapses_nbsp_artifacts():
    text = "Helloa0World\n\n\n\nMore"
    assert normalize_whitespace(text) == "Hello World\n\nMore"


def test_strip_email_boilerplate_removes_unsubscribe(load_fixture):
    html = load_fixture("email", "indeed_html_snippet.html")
    plain = html_to_plain_text(html)
    cleaned = strip_email_boilerplate(plain)
    assert "unsubscribe" not in cleaned.lower()
    assert "Senior Python Engineer" in cleaned


def test_clean_email_body_end_to_end(load_fixture):
    html = load_fixture("email", "indeed_html_snippet.html")
    cleaned = clean_email_body(html)
    assert "Job description" in cleaned or "Senior Python Engineer" in cleaned
    assert "unsubscribe" not in cleaned.lower()


def test_clean_jd_text_is_alias():
    assert clean_jd_text("  hello   world  ") == clean_email_body("  hello   world  ")


def test_clean_email_body_empty():
    assert clean_email_body("") == ""
