"""
Cisco/TCS Interview — Python Coding Drill
=========================================
Run: python interview/sessions/cisco_tcs_coding_drill.py

Practice each problem in 20–25 minutes. Talk through approach before coding.
"""

from collections import defaultdict
from typing import List, Optional


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
# Problem 2: Missing Number (Easy — math / set)
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
    seen = {}
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
# Problem 5: LRU Cache (Medium — design; common for backend roles)
# ---------------------------------------------------------------------------
class LRUCache:
    """O(1) get/put using OrderedDict (interview-friendly). Production: doubly-linked list + hash map."""

    def __init__(self, capacity: int):
        from collections import OrderedDict
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


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
    assert find_missing_num([4, 2, 3, 5, 0]) == 1

    assert two_sum([2, 7, 11, 15], 9) == [0, 1]
    assert two_sum([3, 2, 4], 6) == [1, 2]

    grouped = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    assert sorted(map(sorted, grouped)) == sorted(map(sorted, [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]))

    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)
    assert cache.get(2) == -1

    assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]

    print("All tests passed.")
