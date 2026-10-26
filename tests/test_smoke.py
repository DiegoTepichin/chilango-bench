from importlib.metadata import version

from chilango_bench import __version__


def test_version_matches_package_metadata() -> None:
    assert __version__ == version("chilango-bench")
