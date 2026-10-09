"""Smoke tests for package initialization and CLI invocation."""

from chilango_bench import __version__
from chilango_bench.cli import main


def test_version() -> None:
    """Verify package version is defined."""
    assert __version__ == "0.1.0"


def test_cli_main() -> None:
    """Verify CLI main entrypoint executes cleanly."""
    exit_code = main([])
    assert exit_code == 0
