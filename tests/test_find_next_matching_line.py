from prompt_toolkit.document import Document, branch_coverage_next

def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(branch_coverage_next.values())
    total_branches = len(branch_coverage_next)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage_next.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n")

test_cases = []

for case in test_cases:
    document = Document(text=case["text"], cursor_position=case["cursor_position"])
    result = document.find_next_matching_line(case["match_func"], case["count"])
    assert result == case["expected_result"], f"Test failed for: {case['description']}"
    
    print("\n")
    print(f"Test case: {case['description']}")
    print(f"Expected result: {case['expected_result']}")
    print(f"Actual result: {result}")
    print("Branches hit:")
    for branch, hit in branch_coverage_next.items():
        if hit:
            print(f"  {branch}")
            
print_coverage()