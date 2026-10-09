"""CLI entrypoint for chilango-bench."""

import sys


def main() -> int:
    """Run the chilango-bench command line interface."""
    sys.stdout.write("chilango-bench v0.1.0\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
