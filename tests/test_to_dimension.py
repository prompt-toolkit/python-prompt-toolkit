from prompt_toolkit.layout.dimension import Dimension, to_dimension, to_dimension_coverage
# /home/r0vshan/University/SEP/SEP_python-prompt-toolkit/src/prompt_toolkit/layout/dimension.py This is the correct path
# /home/r0vshan/.local/lib/python3.10/site-packages/prompt_toolkit/layout/dimension.py This is the wrong path

def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(to_dimension_coverage.values())
    total_branches = len(to_dimension_coverage)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in to_dimension_coverage.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n")

# Define test cases
test_cases = [
    (None, "None value (should hit Branch 1)"),
    (69, "Integer value (should hit Branch 2)"),
    (Dimension(), "Dimension instance (should hit Branch 3)"),
    (lambda: 42, "Callable returning an integer (should hit Branch 4)"),
    ("Unsupported type", "Unsupported type (should hit Branch 5)")
]

# Run tests
for value, description in test_cases:
    print(f"\nTesting case: {description}")
    try:
        result = to_dimension(value)
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Exception: {e}")

print_coverage()
