"""
Example of a custom logging handler that uses prompt_toolkit to render nicely
colored logs.
"""
import logging
import time

from prompt_toolkit.shortcuts.logging import PromptToolkitLogHandler


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, handlers=[PromptToolkitLogHandler()])

    for i in range(10):
        logging.debug(f"test debug {i}")
        logging.info(f"test info {i}")
        logging.warning(f"test warning {i}")
        logging.error(f"test error {i}")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
