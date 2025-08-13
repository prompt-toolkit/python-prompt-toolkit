from __future__ import annotations

from prompt_toolkit.shortcuts.input_selection import select_input


def main() -> None:
    result = select_input(
        message="Please select an option:",
        options=[(i, f"Option {i}") for i in range(1, 100)],
    )
    print(result)


if __name__ == "__main__":
    main()
