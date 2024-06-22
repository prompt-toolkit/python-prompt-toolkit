from prompt_toolkit.document import Document, branch_coverage_prev

def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(branch_coverage_prev.values())
    total_branches = len(branch_coverage_prev)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage_prev.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n")

test_cases = [
    {
        "description": "Find the second previous empty line",
        "text": "line 1\n\nline 3\n\nline 5",
        "cursor_position": 18,
        "match_func": lambda line: line.strip() == "",
        "count": 2,
        "expected_result": -3
    },
    {
        "description": "No match found",
        "text": "line 1\nline 2\nline 3\nline 4",
        "cursor_position": 10,
        "match_func": lambda line: line.strip() == "",
        "count": 1,
        "expected_result": None
    },
    {
        "description": "Match before cursor position",
        "text": "line 1\n\nline 3\nline 4",
        "cursor_position": 18,
        "match_func": lambda line: line.strip() == "",
        "count": 1,
        "expected_result": -2
    }
]

for case in test_cases:
    document = Document(text=case["text"], cursor_position=case["cursor_position"])
    result = document.find_previous_matching_line(case["match_func"], case["count"])
    assert result == case["expected_result"], f"Test failed for: {case['description']}"

print_coverage()
