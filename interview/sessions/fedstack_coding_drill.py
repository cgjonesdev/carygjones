"""
Fedstack Interview — Python Coding Drill
==========================================
Run: python interview/sessions/fedstack_coding_drill.py

Practice each problem in 20–25 minutes. Talk through approach before coding.
Federal/backend roles often test fundamentals + practical design (rate limits, validation).
"""

from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional


# ---------------------------------------------------------------------------
# Problem 1: Valid Palindrome (Easy — strings / two pointers)
# ---------------------------------------------------------------------------
def is_palindrome(s: str) -> bool:
    """Return True if s is a palindrome after removing non-alphanumeric chars."""
    cleaned = [c.lower() for c in s if c.isalnum()]
    left, right = 0, len(cleaned) - 1
    while left < right:
        if cleaned[left] != cleaned[right]:
            return False
        left += 1
        right -= 1
    return True


# ---------------------------------------------------------------------------
# Problem 2: Missing Number (Easy — math)
# ---------------------------------------------------------------------------
def find_missing_num(nums: List[int]) -> int:
    """Array contains n distinct numbers in range [0, n]; return the missing one."""
    n = len(nums)
    return n * (n + 1) // 2 - sum(nums)


# ---------------------------------------------------------------------------
# Problem 3: Two Sum (Easy — hash map)
# ---------------------------------------------------------------------------
def two_sum(nums: List[int], target: int) -> List[int]:
    """Return indices of two numbers that add up to target."""
    seen: dict[int, int] = {}
    for i, val in enumerate(nums):
        complement = target - val
        if complement in seen:
            return [seen[complement], i]
        seen[val] = i
    return []


# ---------------------------------------------------------------------------
# Problem 4: Group Anagrams (Medium — hash map)
# ---------------------------------------------------------------------------
def group_anagrams(words: List[str]) -> List[List[str]]:
    groups: dict[tuple, list] = defaultdict(list)
    for word in words:
        key = tuple(sorted(word))
        groups[key].append(word)
    return list(groups.values())


# ---------------------------------------------------------------------------
# Problem 5: Rate Limiter — max N requests per user per window (Medium — design)
# Common for API/security-focused roles
# ---------------------------------------------------------------------------
class RateLimiter:
    """In-memory sliding window: allow at most max_requests per user within window_seconds."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, user_id: str, timestamp: float) -> bool:
        q = self._hits[user_id]
        cutoff = timestamp - self.window_seconds
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.max_requests:
            return False
        q.append(timestamp)
        return True


# ---------------------------------------------------------------------------
# Problem 6: Merge Intervals (Medium — sorting)
# ---------------------------------------------------------------------------
def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    assert is_palindrome("A man, a plan, a canal: Panama")
    assert not is_palindrome("race a car")
    assert is_palindrome(" ")

    assert find_missing_num([0, 1, 3]) == 2
    assert find_missing_num([3, 2, 1]) == 0
    assert find_missing_num([2, 1, 0]) == 3

    assert two_sum([2, 7, 11, 15], 9) == [0, 1]
    assert two_sum([3, 2, 4], 6) == [1, 2]

    grouped = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    assert sorted(map(sorted, grouped)) == sorted(map(sorted, [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]))

    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("user1", 100.0)
    assert limiter.allow("user1", 110.0)
    assert limiter.allow("user1", 120.0)
    assert not limiter.allow("user1", 130.0)
    assert limiter.allow("user1", 161.0)  # first hit expired

    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]

    print("All tests passed.")
