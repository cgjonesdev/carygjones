"""
Heap basics drill (Python heapq)
================================
Run: python interview/sessions/heap_basics_drill.py

Practice heappush / heappop / peek before using heaps in MedianFinder.
"""

from __future__ import annotations

import heapq
from typing import List


# ---------------------------------------------------------------------------
# Problem 1: Push numbers, return them in ascending order via heappop
# ---------------------------------------------------------------------------
def heap_sort_via_heap(nums: List[int]) -> List[int]:
    """Push all nums onto a heap, then pop until empty. Return ascending list."""
    h: List[int] = []
    for n in nums:
        heapq.heappush(h, n)
    out: List[int] = []
    while h:
        out.append(heapq.heappop(h))
    return out


# ---------------------------------------------------------------------------
# Problem 2: Running minimum after each insert
# ---------------------------------------------------------------------------
def running_mins(nums: List[int]) -> List[int]:
    """
    After each number is pushed, record the current heap minimum (h[0]).
    Example: [3, 1, 4, 2] → [3, 1, 1, 1]
    """
    h: List[int] = []
    out: List[int] = []
    for n in nums:
        heapq.heappush(h, n)
        out.append(h[0])
    return out


# ---------------------------------------------------------------------------
# Problem 3: Max via negated min-heap
# ---------------------------------------------------------------------------
def heap_max_sort(nums: List[int]) -> List[int]:
    """
    Use a min-heap of *negated* values to get descending order.
    Example: [3, 1, 4] → [4, 3, 1]
    """
    h: List[int] = []
    for n in nums:
        heapq.heappush(h, -n)
    out: List[int] = []
    while h:
        out.append(-heapq.heappop(h))
    return out


# ---------------------------------------------------------------------------
# Problem 4: K smallest (heap way)
# ---------------------------------------------------------------------------
def k_smallest(nums: List[int], k: int) -> List[int]:
    """Return the k smallest numbers in ascending order."""
    if k <= 0:
        return []
    h: List[int] = []
    for n in nums:
        heapq.heappush(h, n)
    out: List[int] = []
    for _ in range(min(k, len(nums))):
        out.append(heapq.heappop(h))
    return out


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    assert heap_sort_via_heap([3, 1, 4, 1, 5]) == [1, 1, 3, 4, 5]
    assert heap_sort_via_heap([]) == []

    assert running_mins([3, 1, 4, 2]) == [3, 1, 1, 1]
    assert running_mins([5]) == [5]

    assert heap_max_sort([3, 1, 4]) == [4, 3, 1]
    assert heap_max_sort([2, 2, 2]) == [2, 2, 2]

    assert k_smallest([5, 1, 9, 3, 7], 3) == [1, 3, 5]
    assert k_smallest([5, 1, 9], 0) == []
    assert k_smallest([5, 1, 9], 10) == [1, 5, 9]

    print("All heap basics drill tests passed.")
