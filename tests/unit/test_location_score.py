"""Regression tests for location-based match score adjustment."""

from __future__ import annotations

import pytest

from location_score import (
    adjust_match_score,
    apply_location_to_score_data,
    display_match_score,
    is_acceptable_location,
    is_la_or_sf_bay,
    is_remote,
)


@pytest.mark.parametrize(
    "location,expected",
    [
        ("Remote", True),
        ("United States (Remote)", True),
        ("Work from home", True),
        ("Los Angeles, CA", True),
        ("San Jose, CA", True),
        ("Bay Area", True),
        ("Austin, TX", False),
        ("", False),
        (None, False),
    ],
)
def test_is_acceptable_location(location, expected):
    assert is_acceptable_location(location) is expected


@pytest.mark.parametrize(
    "location,expected",
    [
        ("Remote", True),
        ("#LI-Remote", True),
        ("Distributed team", True),
        ("On-site Los Angeles", False),
    ],
)
def test_is_remote(location, expected):
    assert is_remote(location) is expected


@pytest.mark.parametrize(
    "location,expected",
    [
        ("Los Angeles, CA", True),
        ("Temple City", True),
        ("San Francisco", True),
        ("Palo Alto", True),
        ("Chicago, IL", False),
    ],
)
def test_is_la_or_sf_bay(location, expected):
    assert is_la_or_sf_bay(location) is expected


@pytest.mark.parametrize(
    "score,location,expected",
    [
        (85, "Remote", 85),
        (85, "Los Angeles, CA", 85),
        (85, "Austin, TX", 8),
        (75, "New York, NY", 8),
        (0, "Denver, CO", 0),
    ],
)
def test_adjust_match_score(score, location, expected):
    assert adjust_match_score(score, location) == expected


def test_apply_location_to_score_data_penalizes_and_sets_should_generate():
    data = apply_location_to_score_data(
        {"match_score": 85, "location": "Austin, TX"},
        threshold=80,
    )
    assert data["match_score"] == 8
    assert data["raw_match_score"] == 85
    assert data["should_generate"] is False


def test_apply_location_to_score_data_remote_passes_threshold():
    data = apply_location_to_score_data(
        {"match_score": 85, "location": "Remote"},
        threshold=80,
    )
    assert data["match_score"] == 85
    assert "raw_match_score" not in data
    assert data["should_generate"] is True


def test_display_match_score_legacy_recomputes():
    meta = {"match_score": 85, "location": "Austin, TX"}
    assert display_match_score(meta) == 8


def test_display_match_score_uses_stored_adjusted_value():
    meta = {"match_score": 8, "raw_match_score": 85, "location": "Austin, TX"}
    assert display_match_score(meta) == 8


def test_display_match_score_none_when_missing():
    assert display_match_score({}) is None
