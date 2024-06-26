from prompt_toolkit.document import Document, branch_coverage_translate


DOC = Document(
    "line 1\n" + "line 2\n" + "line 3\n" + "line 4\n", len("line 1\n" + "lin")
)


test_cases = [
    ((0, 0), "Test 1: Basic case with first row and first column"),
    ((0, 5), "Test 2: First row with a valid column index within range"),
    ((1, 0), "Test 3: Second row, first column"),
    ((-1000, 0), "Test 4: Negative row index"),
    ((0, -1), "Test 5: Negative column index"),
    ((10, 0), "Test 6: Row index out of range (greater than number of lines)"),
    ((0, 100), "Test 7: Column index out of range (greater than line length)"),
    ((10, 100), "Test 8: Both row and column indices out of range"),
    ((-1, -1), "Test 9: Both row and column indices negative"),
]


def print_coverage():
    print("\nCoverage report:")
    hit_branches = sum(branch_coverage_translate.values())
    total_branches = len(branch_coverage_translate)
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage_translate.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(
        f"Coverage: {hit_branches}/{total_branches} branches hit ({coverage_percentage:.2f}%)\n"
    )


def test(document):
    for (row, col), description in test_cases:
        try:
            result = document.translate_row_col_to_index(row, col)
            print(f"{description}: Success, Result = {result}")
        except Exception as e:
            print(f"{description}: Failed with exception: {e}")


test(DOC)
print_coverage()
