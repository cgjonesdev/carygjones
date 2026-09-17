"""
NextEra / US Tech — Coding Drill Round 2 (post phone screen)
=============================================================
Run: python interview/sessions/nextera_coding_drill_2.py

Focus: practical backend patterns + common screen problems.
Talk through approach BEFORE coding (2–3 min).
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Deque, Dict, List, Optional


# ---------------------------------------------------------------------------
# Problem 1: Two Sum (Easy — hash map)
# ---------------------------------------------------------------------------
def two_sum(nums: List[int], target: int) -> List[int]:
    """Return indices of two numbers that add up to target. Assume one solution."""
    seen: Dict[int, int] = {}
    for i, val in enumerate(nums):
        need = target - val
        if need in seen:
            return [seen[need], i]
        seen[val] = i
    return []


# ---------------------------------------------------------------------------
# Problem 2: Valid parentheses (Easy — stack)
# ---------------------------------------------------------------------------
def is_valid_parentheses(s: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: List[str] = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return not stack


# ---------------------------------------------------------------------------
# Problem 3: Top K frequent elements (Medium — hash + sort/heap)
# ---------------------------------------------------------------------------
def top_k_frequent(nums: List[int], k: int) -> List[int]:
    """Return the k most frequent numbers (any order OK among ties at boundary)."""
    counts = Counter(nums)
    # sort by frequency descending, take k
    return [val for val, _ in sorted(counts.items(), key=lambda x: -x[1])[:k]]


# ---------------------------------------------------------------------------
# Problem 4: Binary tree level-order traversal (Medium — BFS)
# ---------------------------------------------------------------------------
class TreeNode:
    def __init__(self, val: int = 0, left: "TreeNode" = None, right: "TreeNode" = None):
        self.val = val
        self.left = left
        self.right = right


def level_order(root: Optional[TreeNode]) -> List[List[int]]:
    if not root:
        return []
    out: List[List[int]] = []
    q: Deque[TreeNode] = deque([root])
    while q:
        level: List[int] = []
        for _ in range(len(q)):
            node = q.popleft()
            level.append(node.val)
            if node.left:
                q.append(node.left)
            if node.right:
                q.append(node.right)
        out.append(level)
    return out


# ---------------------------------------------------------------------------
# Problem 5: Running median of a stream (Hard-ish — two heaps concept)
# For drill: simpler version — median of a static list after each insert
# We'll implement insert + find_median with sorted list for clarity in interview
# ---------------------------------------------------------------------------
class MedianFinder:
    """Naive O(n) insert via sorted list — fine to explain; mention heaps as upgrade."""

    def __init__(self):
        self._data: List[float] = []

    def add_num(self, num: float) -> None:
        # insert in sorted order
        lo, hi = 0, len(self._data)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._data[mid] < num:
                lo = mid + 1
            else:
                hi = mid
        self._data.insert(lo, num)

    def find_median(self) -> float:
        n = len(self._data)
        if n == 0:
            raise ValueError("empty")
        mid = n // 2
        if n % 2:
            return float(self._data[mid])
        return (self._data[mid - 1] + self._data[mid]) / 2.0


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]
    assert two_sum([3, 2, 4], 6) == [1, 2]

    assert is_valid_parentheses("()") is True
    assert is_valid_parentheses("()[]{}") is True
    assert is_valid_parentheses("(]") is False
    assert is_valid_parentheses("([)]") is False
    assert is_valid_parentheses("{[]}") is True
    assert is_valid_parentheses("") is True

    assert sorted(top_k_frequent([1, 1, 1, 2, 2, 3], 2)) == [1, 2]
    assert top_k_frequent([1], 1) == [1]

    #     3
    #    / \
    #   9  20
    #     /  \
    #    15   7
    root = TreeNode(3, TreeNode(9), TreeNode(20, TreeNode(15), TreeNode(7)))
    assert level_order(root) == [[3], [9, 20], [15, 7]]
    assert level_order(None) == []

    mf = MedianFinder()
    mf.add_num(1)
    assert mf.find_median() == 1.0
    mf.add_num(2)
    assert mf.find_median() == 1.5
    mf.add_num(3)
    assert mf.find_median() == 2.0

    print("All NextEra coding drill 2 tests passed.")
