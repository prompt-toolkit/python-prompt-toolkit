import pytest

from prompt_toolkit.buffer import Buffer, branch_coverage_insert


@pytest.fixture
def _buffer():
    buff = Buffer()
    return buff


test_cases = [
    (True, "Test 1: Insert line above with copy_margin=True"),
    (False, "Test 2: Insert line above with copy_margin=False"),
]


def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(branch_coverage_insert.values())
    total_branches = len(branch_coverage_insert)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage_insert.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(
        f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n"
    )


def test_insert_line_above(_buffer):
    for copy_margin, description in test_cases:
        try:
            _buffer.insert_line_above(copy_margin)
        except Exception as e:
            print(f"{description}: Failed with exception: {e}")


print_coverage()
