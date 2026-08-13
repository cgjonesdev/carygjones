"""Regression tests for recruiter reply text generation."""

from __future__ import annotations

from reply_generator import (
    build_reply_body,
    extract_bullets,
    is_noreply_address,
    recruiter_first_name,
    reply_subject,
)


def test_is_noreply_matches_app_settings():
    from app_settings import is_noreply_address as settings_noreply

    addrs = ["", "no-reply@ashbyhq.com", "jane@acme.com"]
    for addr in addrs:
        assert is_noreply_address(addr) == settings_noreply(addr)


def test_recruiter_first_name_human():
    assert recruiter_first_name("Jane Doe <jane@acme.com>", company="Acme") == "Jane"


def test_recruiter_first_name_noreply():
    assert recruiter_first_name("Jobs <no-reply@ashbyhq.com>", company="Acme") == "Acme team"


def test_reply_subject_from_source():
    meta = {"role": "Engineer", "company": "Acme"}
    source = {"subject": "Opportunity at Acme"}
    assert reply_subject(meta, source) == "Re: Opportunity at Acme"


def test_reply_subject_already_re():
    meta = {"role": "Engineer", "company": "Acme"}
    source = {"subject": "Re: Opportunity"}
    assert reply_subject(meta, source) == "Re: Opportunity"


def test_reply_subject_fallback():
    meta = {"role": "Engineer", "company": "Acme"}
    assert reply_subject(meta, None) == "Re: Engineer — Acme"


def test_build_reply_body_includes_bullets():
    body = build_reply_body(
        greeting="Jane",
        meta={"company": "Acme", "role": "Engineer", "location": "Remote"},
        contact={"name": "Cary Jones", "email": "cary@example.com", "phone": "", "linkedin": "", "website": ""},
        bullets=["Built APIs at scale", "Led Python teams"],
    )
    assert "Hi Jane," in body
    assert "Built APIs at scale" in body
    assert "Cary Jones" in body


def test_extract_bullets_from_html(tmp_path):
    cover = tmp_path / "cover_letter.html"
    cover.write_text(
        "<ul><li>First bullet</li><li>Second bullet</li><li>Third</li></ul>",
        encoding="utf-8",
    )
    bullets = extract_bullets(cover, max_bullets=2)
    assert bullets == ["First bullet", "Second bullet"]
