"""Regression tests for local/remote meta.json merge (prevents interview clobber)."""

from __future__ import annotations

import json

import pytest

from app_meta_merge import (
    application_status,
    merge_application_meta,
    merge_interview_notes,
    merge_meta_files,
    local_should_win_over_remote,
)


def test_application_status_defaults_to_ready():
    assert application_status({}) == "ready"


def test_nextera_style_interview_clobber(load_json_fixture):
    remote = load_json_fixture("meta", "interview_clobber_remote.json")
    local = load_json_fixture("meta", "interview_clobber_local.json")
    merged, push = merge_application_meta(local, remote)
    assert merged["status"] == "interview"
    assert merged["interview_url"] == "https://zoom.us/j/123"
    assert push is True


def test_stale_gcs_pull_preserves_local_interview_notes():
    remote = {
        "status": "applied",
        "updated": "2026-08-12",
        "notes": "protocol updated meta",
    }
    local = {
        "status": "interview",
        "updated": "2026-08-12",
        "interview_notes": "Round 1 — asked about Django ORM",
    }
    merged, push = merge_application_meta(local, remote)
    assert merged["interview_notes"] == "Round 1 — asked about Django ORM"
    assert push is True


def test_newer_remote_interview_notes_win():
    remote = {
        "status": "interview",
        "updated": "2026-08-13",
        "interview_notes": "Saved from Cloud Run",
    }
    local = {
        "status": "interview",
        "updated": "2026-08-12",
        "interview_notes": "Older local draft",
    }
    merged, push = merge_application_meta(local, remote)
    assert merged["interview_notes"] == "Saved from Cloud Run"


def test_local_should_win_interview_over_applied():
    local = {"status": "interview", "updated": "2026-08-12"}
    remote = {"status": "applied", "updated": "2026-08-12"}
    assert local_should_win_over_remote(local, remote) is True


def test_merge_interview_notes_both_empty_removes_key():
    merged: dict = {"interview_notes": "old"}
    merge_interview_notes({}, {}, merged)
    assert "interview_notes" not in merged


def test_merge_meta_files_round_trip():
    remote = json.dumps({"status": "ready", "updated": "2026-08-01"})
    local = json.dumps({"status": "interview", "updated": "2026-08-12", "interview_url": "https://x"})
    text, push = merge_meta_files(local, remote)
    parsed = json.loads(text)
    assert parsed["status"] == "interview"
    assert push is True


def test_no_local_returns_remote_copy():
    remote = {"status": "ready", "company": "Weave"}
    merged, push = merge_application_meta(None, remote)
    assert merged == remote
    assert push is False
