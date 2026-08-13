"""Regression tests for LinkedIn job ID parsing and applied detection."""

from __future__ import annotations

import pytest

from phases.linkedin_applied import (
    collect_job_ids,
    is_applied_signal,
    job_id_from_meta,
    job_id_from_value,
    linkedin_job_open_url,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("4364914924", "4364914924"),
        ("https://www.linkedin.com/jobs/view/4364914924/", "4364914924"),
        ("https://www.linkedin.com/comm/jobs/view/4364914924", "4364914924"),
        ("", None),
        (None, None),
        ("not-a-url", None),
    ],
)
def test_job_id_from_value(value, expected):
    assert job_id_from_value(value) == expected


def test_job_id_from_meta_prefers_linkedin_job_id():
    meta = {
        "linkedin_job_id": "111",
        "apply_url": "https://www.linkedin.com/jobs/view/222/",
    }
    assert job_id_from_meta(meta) == "111"


def test_job_id_from_meta_falls_back_to_apply_url():
    meta = {"apply_url": "https://www.linkedin.com/jobs/view/222/"}
    assert job_id_from_meta(meta) == "222"


def test_linkedin_job_open_url_canonical():
    url = linkedin_job_open_url(
        "https://www.linkedin.com/comm/jobs/view/4364914924",
        None,
    )
    assert url == "https://www.linkedin.com/jobs/view/4364914924/"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ({"applied": True}, True),
        ({"applicationStatus": "applied"}, True),
        ({"applicationStatus": "not applied"}, False),
        ({"status": "open"}, False),
        ("not a dict", False),
    ],
)
def test_is_applied_signal(raw, expected):
    assert is_applied_signal(raw) is expected


def test_collect_job_ids_from_search_results():
    jobs = [
        {
            "jobId": "123",
            "jobUrl": "https://www.linkedin.com/jobs/view/123/",
            "applicationStatus": "applied",
        },
        {
            "jobId": "456",
            "jobUrl": "https://www.linkedin.com/jobs/view/456/",
            "applicationStatus": "open",
        },
    ]
    ids = collect_job_ids(jobs, assume_applied=False)
    assert ids == {"123"}


def test_collect_job_ids_assume_applied():
    jobs = [{"jobId": "789", "jobUrl": "https://www.linkedin.com/jobs/view/789/"}]
    ids = collect_job_ids(jobs, assume_applied=True)
    assert ids == {"789"}
