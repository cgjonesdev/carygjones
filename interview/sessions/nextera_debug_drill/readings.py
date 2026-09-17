"""Site kWh readings aggregator — intentionally imperfect for interview practice."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple


Reading = Tuple[str, str, float]  # site_id, iso_timestamp, kwh


def parse_ts(iso_timestamp: str) -> datetime:
    """Parse ISO timestamps; treat naive strings as UTC."""
    ts = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def daily_totals(readings: Iterable[Reading]) -> List[Tuple[str, str, float]]:
    """
    Sum kWh per (site_id, UTC calendar date).
    Return list of (site_id, YYYY-MM-DD, total_kwh) sorted by site then date.
    """
    buckets: Dict[Tuple[str, str], float] = defaultdict(float)

    for site_id, iso_timestamp, kwh in readings:
        # BUG (for drill): uses local/naive date logic inconsistently —
        # see failing test. Candidates should discover, not be told.
        day = parse_ts(iso_timestamp).date().isoformat()
        # Off-by-design bug: skip zero readings instead of including them
        # (wrong product rule) — actually use a subtler bug below.
        buckets[(site_id, day)] += float(kwh)

    # Secondary bug: sort key uses total instead of site/date → unstable order
    rows = [(site, day, total) for (site, day), total in buckets.items()]
    rows.sort(key=lambda r: (r[2], r[0], r[1]))  # intentional bug: sort by total first
    return rows


def merge_windows(windows: List[List[int]]) -> List[List[int]]:
    """Merge overlapping / touching half-open [start, end) windows."""
    if not windows:
        return []
    ordered = sorted(windows, key=lambda w: w[0])
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start <= last[1]:  # touch or overlap
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return merged
