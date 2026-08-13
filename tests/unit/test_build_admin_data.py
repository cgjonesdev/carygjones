"""Regression tests for admin dashboard data builders."""

from __future__ import annotations

import build_admin_data


def test_gmail_url_from_message_id():
    meta = {"source_email": {"message_id": "abc123def456"}}
    url = build_admin_data.gmail_url(meta)
    assert url == "https://mail.google.com/mail/u/0/#inbox/abc123def456"


def test_gmail_url_missing():
    assert build_admin_data.gmail_url({}) is None


def test_build_links_includes_core_actions():
    meta = {
        "apply_url": "https://apply.example.com",
        "interview_url": "https://zoom.us/j/1",
        "source_email": {"message_id": "abc"},
    }
    links = build_admin_data.build_links("weave", meta, pages_base="https://example.com")
    labels = [link["label"] for link in links]
    assert labels == ["Apply", "Interview", "Gmail", "Resume", "Cover", "Prep"]
    assert links[0]["url"] == "https://apply.example.com"


def test_prep_source_slugs_explicit_and_aliases():
    slugs = build_admin_data.prep_source_slugs(
        "ustechsolutions",
        {"prep_slug": "custom"},
    )
    assert slugs[0] == "custom"
    assert "nextera" in slugs


def test_prep_source_slugs_default_slug_first():
    slugs = build_admin_data.prep_source_slugs("weave")
    assert slugs[0] == "weave"
