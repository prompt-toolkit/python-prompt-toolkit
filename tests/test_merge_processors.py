from prompt_toolkit.layout.processors import merge_processors, merge_processors_coverage
from prompt_toolkit.layout.processors import Processor, DummyProcessor, _MergedProcessor

def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(merge_processors_coverage.values())
    total_branches = len(merge_processors_coverage)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in merge_processors_coverage.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n")

class MockProcessor(Processor):
    def apply_transformation(self, *args, **kwargs):
        pass

test_cases = [
    ([], "Empty list of processors (should hit Branch 1)"),
    ([MockProcessor()], "Single processor (should hit Branch 2)"),
    ([MockProcessor(), MockProcessor()], "Multiple processors (should hit Branch 3)")
]

for processors, description in test_cases:
    print(f"\nTesting case: {description}")
    result = merge_processors(processors)
    print(f"Result: {result}")

print_coverage()
