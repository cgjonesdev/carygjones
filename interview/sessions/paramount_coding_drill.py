"""
Paramount+ / Media Platform — Python Coding Drill
=================================================
Run: python interview/sessions/paramount_coding_drill.py

Practice talking through approach BEFORE coding (2–3 min).
Target: 20–25 min per problem in mock interview conditions.
"""

from __future__ import annotations

import json
import time
from collections import Counter, OrderedDict, defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Challenge 1: LRU Cache (Medium — caching metadata / session tokens)
# Interviewer prompt:
#   "Implement an LRU cache for API responses. get and put must be O(1)."
# ---------------------------------------------------------------------------
class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Challenge 2: Merge overlapping intervals (Medium — broadcast windows)
# Interviewer prompt:
#   "Given [start, end] intervals, merge all overlapping intervals."
# Example: [[1,3],[2,6],[8,10],[15,18]] -> [[1,6],[8,10],[15,18]]
# ---------------------------------------------------------------------------
def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0][:]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


# ---------------------------------------------------------------------------
# Challenge 3: Top K frequent elements (Medium — content popularity)
# Interviewer prompt:
#   "Return the k most frequently streamed content IDs."
# ---------------------------------------------------------------------------
def top_k_frequent(ids: List[str], k: int) -> List[str]:
    counts = Counter(ids)
    # Bucket sort O(n) when k << n; interview also accepts heap O(n log k)
    buckets: List[List[str]] = [[] for _ in range(len(ids) + 1)]
    for content_id, freq in counts.items():
        buckets[freq].append(content_id)
    result: List[str] = []
    for freq in range(len(buckets) - 1, 0, -1):
        for content_id in buckets[freq]:
            result.append(content_id)
            if len(result) == k:
                return result
    return result


# ---------------------------------------------------------------------------
# Challenge 4: Idempotent Lambda-style handler (Paramount serverless pattern)
# Interviewer prompt:
#   "SQS may deliver duplicates. Make this handler safe to retry."
# ---------------------------------------------------------------------------
@dataclass
class ProcessResult:
    status: str
    asset_id: str


class AssetProcessor:
    """Sketch: thin handler + idempotent service (DynamoDB conditional write)."""

    def __init__(self, store: Dict[str, str]):
        self._processed = store  # stand-in for DynamoDB idempotency table

    def handle(self, event: dict) -> ProcessResult:
        asset_id = event["asset_id"]
        idempotency_key = event.get("message_id") or asset_id

        if idempotency_key in self._processed:
            return ProcessResult(status="duplicate", asset_id=asset_id)

        # business logic
        metadata = self._extract_metadata(event)
        self._persist(asset_id, metadata)

        self._processed[idempotency_key] = "done"
        return ProcessResult(status="processed", asset_id=asset_id)

    def _extract_metadata(self, event: dict) -> dict:
        return {"title": event.get("title"), "duration_sec": event.get("duration_sec")}

    def _persist(self, asset_id: str, metadata: dict) -> None:
        pass  # write to catalog


# ---------------------------------------------------------------------------
# Challenge 5: Rate limiter — sliding window (API / partner integrations)
# Interviewer prompt:
#   "Allow at most `limit` requests per `window_sec` per partner_id."
# ---------------------------------------------------------------------------
class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_sec: float):
        self.limit = limit
        self.window_sec = window_sec
        self._hits: Dict[str, List[float]] = defaultdict(list)

    def allow(self, partner_id: str, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        window_start = now - self.window_sec
        hits = [t for t in self._hits[partner_id] if t > window_start]
        if len(hits) >= self.limit:
            self._hits[partner_id] = hits
            return False
        hits.append(now)
        self._hits[partner_id] = hits
        return True


# ---------------------------------------------------------------------------
# Challenge 6: Parse simple HLS-style manifest lines (Media-adjacent)
# Interviewer prompt:
#   "Parse #EXTINF duration lines and following URI lines into segments."
# ---------------------------------------------------------------------------
def parse_extinf_manifest(text: str) -> List[dict]:
    segments: List[dict] = []
    pending_duration: Optional[float] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            duration_str = line.split(":", 1)[1].split(",", 1)[0]
            pending_duration = float(duration_str)
        elif not line.startswith("#") and pending_duration is not None:
            segments.append({"duration": pending_duration, "uri": line})
            pending_duration = None
    return segments


# ---------------------------------------------------------------------------
# Tests (run after you implement from scratch in practice)
# ---------------------------------------------------------------------------
def _run_tests() -> None:
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1
    cache.put("c", 3)
    assert cache.get("b") is None

    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]

    assert top_k_frequent(["a", "b", "a", "c", "a", "b"], 2) == ["a", "b"]

    proc = AssetProcessor({})
    r1 = proc.handle({"asset_id": "x1", "message_id": "m1", "title": "Pilot"})
    r2 = proc.handle({"asset_id": "x1", "message_id": "m1", "title": "Pilot"})
    assert r1.status == "processed" and r2.status == "duplicate"

    limiter = SlidingWindowRateLimiter(limit=2, window_sec=10)
    t0 = 1000.0
    assert limiter.allow("partner-a", t0)
    assert limiter.allow("partner-a", t0 + 1)
    assert not limiter.allow("partner-a", t0 + 2)
    assert limiter.allow("partner-a", t0 + 11)

    manifest = """#EXTM3U
#EXTINF:6.0,
seg0.ts
#EXTINF:4.5,
seg1.ts
"""
    segs = parse_extinf_manifest(manifest)
    assert segs == [{"duration": 6.0, "uri": "seg0.ts"}, {"duration": 4.5, "uri": "seg1.ts"}]

    print("All Paramount coding drill tests passed.")


if __name__ == "__main__":
    _run_tests()
