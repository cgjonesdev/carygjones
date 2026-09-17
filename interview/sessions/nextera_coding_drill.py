"""
NextEra / US Tech Solutions — Python Coding Drill
==================================================
Run: python interview/sessions/nextera_coding_drill.py

Role focus: backend/cloud/SQL + legacy modernization (AI is bonus).
Practice each problem in 20–25 minutes. Talk through approach BEFORE coding.

Problems:
  1. Reconcile ledgers (legacy vs modern) — hash map / set
  2. Aggregate site readings by day — grouping / datetime
  3. Merge maintenance windows — intervals
  4. Migration deploy order — topological sort
  5. Sliding-window rate limit on telemetry — deque
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime
from typing import Deque, Dict, Iterable, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Problem 1: Reconcile ledgers (Easy–Medium)
# ---------------------------------------------------------------------------
# Legacy and modern systems both emit rows: (txn_id, amount_cents).
# Return txn_ids that are mismatched:
#   - present in only one system, OR
#   - present in both with different amounts
# Preserve discovery order: first time a txn_id appears in either stream
# (legacy first, then modern), collect unique mismatched ids.
# ---------------------------------------------------------------------------
def reconcile_ledgers(
    legacy: List[Tuple[str, int]],
    modern: List[Tuple[str, int]],
) -> List[str]:
    """Return mismatched txn_ids in first-seen order (legacy then modern)."""
    legacy_map = {txn: amt for txn, amt in legacy}
    modern_map = {txn: amt for txn, amt in modern}
    seen: Set[str] = set()
    out: List[str] = []
    for txn, _ in legacy + modern:
        if txn in seen:
            continue
        seen.add(txn)
        if legacy_map.get(txn) != modern_map.get(txn):
            out.append(txn)
    return out


# ---------------------------------------------------------------------------
# Problem 2: Daily site totals (Easy–Medium)
# ---------------------------------------------------------------------------
# Readings: (site_id, iso_timestamp, kwh). Sum kWh per (site_id, UTC date).
# Return list of (site_id, "YYYY-MM-DD", total_kwh) sorted by site then date.
# ---------------------------------------------------------------------------
def daily_site_totals(
    readings: List[Tuple[str, str, float]],
) -> List[Tuple[str, str, float]]:
    totals: Dict[Tuple[str, str], float] = defaultdict(float)
    for site_id, ts, kwh in readings:
        day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date().isoformat()
        totals[(site_id, day)] += kwh
    return [
        (site, day, round(total, 6))
        for (site, day), total in sorted(totals.items(), key=lambda x: (x[0][0], x[0][1]))
    ]


# ---------------------------------------------------------------------------
# Problem 3: Merge maintenance windows (Medium)
# ---------------------------------------------------------------------------
# Windows are [start, end) half-open intervals on a timeline (ints).
# Merge overlaps / contiguous ranges. Return sorted non-overlapping list.
# ---------------------------------------------------------------------------
def merge_windows(windows: List[List[int]]) -> List[List[int]]:
    if not windows:
        return []
    windows = sorted(windows, key=lambda w: w[0])
    merged = [windows[0][:]]
    for start, end in windows[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


# ---------------------------------------------------------------------------
# Problem 4: Migration deploy order (Medium)
# ---------------------------------------------------------------------------
# services: list of service names
# deps: list of (service, depends_on) — service cannot deploy until depends_on is live
# Return a valid deploy order, or [] if a cycle exists.
# Prefer lexicographically smallest among valid orders (Kahn + min-heap/sort).
# ---------------------------------------------------------------------------
def migration_order(
    services: List[str],
    deps: List[Tuple[str, str]],
) -> List[str]:
    indegree = {s: 0 for s in services}
    graph: Dict[str, List[str]] = {s: [] for s in services}
    for svc, depends_on in deps:
        graph[depends_on].append(svc)
        indegree[svc] += 1

    ready = sorted([s for s, d in indegree.items() if d == 0])
    order: List[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for nxt in graph[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
                ready.sort()
    return order if len(order) == len(services) else []


# ---------------------------------------------------------------------------
# Problem 5: Telemetry rate limiter (Medium)
# ---------------------------------------------------------------------------
# Allow at most max_events per site_id inside a sliding window of window_seconds.
# allow(site_id, timestamp) -> True if accepted (and recorded), else False.
# ---------------------------------------------------------------------------
class TelemetryRateLimiter:
    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, site_id: str, timestamp: float) -> bool:
        q = self._hits[site_id]
        cutoff = timestamp - self.window_seconds
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.max_events:
            return False
        q.append(timestamp)
        return True


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    assert reconcile_ledgers(
        [("a", 100), ("b", 200), ("c", 300)],
        [("a", 100), ("b", 250), ("d", 400)],
    ) == ["b", "c", "d"]
    assert reconcile_ledgers([], [("x", 1)]) == ["x"]
    assert reconcile_ledgers([("x", 1)], [("x", 1)]) == []

    assert daily_site_totals(
        [
            ("S1", "2026-08-20T10:00:00Z", 1.5),
            ("S1", "2026-08-20T22:00:00Z", 2.5),
            ("S2", "2026-08-20T09:00:00Z", 3.0),
            ("S1", "2026-08-21T01:00:00Z", 4.0),
        ]
    ) == [
        ("S1", "2026-08-20", 4.0),
        ("S1", "2026-08-21", 4.0),
        ("S2", "2026-08-20", 3.0),
    ]

    assert merge_windows([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]
    assert merge_windows([[1, 4], [4, 5]]) == [[1, 5]]
    assert merge_windows([]) == []

    assert migration_order(
        ["api", "db", "cache", "worker"],
        [("api", "db"), ("api", "cache"), ("worker", "api")],
    ) == ["cache", "db", "api", "worker"]
    assert migration_order(["a", "b"], [("a", "b"), ("b", "a")]) == []

    lim = TelemetryRateLimiter(max_events=2, window_seconds=10)
    assert lim.allow("S1", 0.0) is True
    assert lim.allow("S1", 5.0) is True
    assert lim.allow("S1", 6.0) is False
    assert lim.allow("S1", 10.1) is True
    assert lim.allow("S2", 6.0) is True

    print("All NextEra coding drill tests passed.")
