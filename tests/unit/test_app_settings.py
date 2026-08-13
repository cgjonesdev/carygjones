"""Regression tests for admin meta settings and noreply detection."""

from __future__ import annotations

import pytest
from freezegun import freeze_time

from app_settings import (
    apply_settings_update,
    apply_source_email_to_meta,
    is_noreply_address,
    normalize_status,
    parse_gmail_message_id,
    parse_sender_fields,
    recruiter_email_from_meta,
    recruiter_name_from_meta,
    settings_from_meta,
)


@pytest.mark.parametrize(
    "addr,expected",
    [
        ("", True),
        ("no-reply@ashbyhq.com", True),
        ("jobs@match.indeed.com", True),
        ("michael.gonzales@ustechsolutions.com", False),
        ("recruiting@company.com", False),
    ],
)
def test_is_noreply_address(addr, expected):
    assert is_noreply_address(addr) is expected


def test_parse_sender_fields():
    name, addr = parse_sender_fields("Michael Gonzales <michael.gonzales@ustechsolutions.com>")
    assert name == "Michael Gonzales"
    assert addr == "michael.gonzales@ustechsolutions.com"


def test_recruiter_email_from_meta_direct():
    meta = {"recruiter_email": "human@company.com"}
    assert recruiter_email_from_meta(meta) == "human@company.com"


def test_recruiter_email_from_meta_skips_noreply_source():
    meta = {
        "source_email": {
            "sender": "Commure Talent Team <no-reply@ashbyhq.com>",
        }
    }
    assert recruiter_email_from_meta(meta) == ""


def test_recruiter_email_from_meta_notes_fallback():
    meta = {"notes": "Recruiter: Jane Doe <jane@example.com>"}
    assert recruiter_email_from_meta(meta) == "jane@example.com"


def test_recruiter_name_from_meta():
    meta = {"recruiter_name": "Michael"}
    assert recruiter_name_from_meta(meta) == "Michael"


def test_apply_source_email_to_meta_populates_recruiter():
    meta = apply_source_email_to_meta(
        {},
        {
            "message_id": "abc123",
            "thread_id": "abc123",
            "subject": "Role at Acme",
            "sender": "Jane Recruiter <jane@acme.com>",
        },
    )
    assert meta["recruiter_email"] == "jane@acme.com"
    assert meta["recruiter_name"] == "Jane"
    assert meta["source_email"]["message_id"] == "abc123"


def test_parse_gmail_message_id_from_url():
    url = "https://mail.google.com/mail/u/0/#inbox/19ff2748425fed31"
    assert parse_gmail_message_id(url) == "19ff2748425fed31"


def test_parse_gmail_message_id_raw():
    assert parse_gmail_message_id("19ff2748425fed31") == "19ff2748425fed31"


def test_normalize_status_valid():
    assert normalize_status("Interview") == "interview"


def test_normalize_status_invalid():
    with pytest.raises(ValueError, match="Invalid status"):
        normalize_status("bogus")


@freeze_time("2026-08-12")
def test_apply_settings_update():
    meta = apply_settings_update(
        {"company": "Weave"},
        {
            "recruiter_email": "jane@acme.com",
            "recruiter_name": "Jane",
            "status": "interview",
            "notes": "Screen tomorrow",
        },
    )
    assert meta["status"] == "interview"
    assert meta["updated"] == "2026-08-12"
    assert meta["recruiter_email"] == "jane@acme.com"


def test_settings_from_meta():
    meta = {
        "recruiter_email": "jane@acme.com",
        "status": "ready",
        "source_email": {"message_id": "abc", "subject": "Hello"},
    }
    settings = settings_from_meta(meta)
    assert settings["recruiter_email"] == "jane@acme.com"
    assert settings["gmail_message_id"] == "abc"
