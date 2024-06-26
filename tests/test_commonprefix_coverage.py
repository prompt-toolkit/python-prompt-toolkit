from __future__ import annotations
from typing import Iterable, List, Tuple
from prompt_toolkit.completion.base import branch_coverage,_commonprefix

def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(branch_coverage.values())
    total_branches = len(branch_coverage)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n")


# Tests
test_cases: List[Tuple[List[str], str]] = [
    (["car", "car"], "Test 1: Same words"),
    ([], "Test 2: Empty list"),
    (["car", "dog"], "Test 2: Different words")
]

for strings, description in test_cases:
    print(f"\nTesting case: {description} - Input: {strings}")
    result = _commonprefix(strings)
    print("Common prefix:", result)

print_coverage()

