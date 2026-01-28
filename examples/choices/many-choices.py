from __future__ import annotations

from prompt_toolkit.shortcuts import choice


def main() -> None:
    result = choice(
        message="Please select an option:",
        options=[(i, f"Option {i}") for i in range(1, 100)],
    )
    print(result)


if __name__ == "__main__":
    main()
