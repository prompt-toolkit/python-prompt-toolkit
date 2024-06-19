from prompt_toolkit.layout.dimension import branch_coverage,is_dimension


def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(branch_coverage.values())
    total_branches = len(branch_coverage)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n")


# Tests
test_cases = []

for value, description in test_cases:
    print(f"\nTesting case: {description}")
    result = is_dimension(value)
    print(f"Result: {result}")

print_coverage()