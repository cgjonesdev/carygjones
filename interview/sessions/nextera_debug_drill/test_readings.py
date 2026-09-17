"""Failing tests for the NextEra-style debug drill."""

from readings import daily_totals, merge_windows


def test_daily_totals_groups_by_site_and_utc_date():
    readings = [
        ("S1", "2026-09-01T23:30:00Z", 10.0),
        ("S1", "2026-09-02T00:15:00Z", 5.0),
        ("S2", "2026-09-01T12:00:00Z", 3.0),
        ("S1", "2026-09-01T10:00:00Z", 2.0),
    ]
    assert daily_totals(readings) == [
        ("S1", "2026-09-01", 12.0),
        ("S1", "2026-09-02", 5.0),
        ("S2", "2026-09-01", 3.0),
    ]


def test_daily_totals_empty():
    assert daily_totals([]) == []


def test_merge_windows_overlaps_and_touching():
    assert merge_windows([[1, 3], [2, 6], [8, 10], [15, 18]]) == [
        [1, 6],
        [8, 10],
        [15, 18],
    ]
    assert merge_windows([[1, 4], [4, 5]]) == [[1, 5]]
