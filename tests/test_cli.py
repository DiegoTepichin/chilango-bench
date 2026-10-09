"""Unit and integration tests for CLI interface commands."""

from pathlib import Path

from chilango_bench.cli import main


def test_cli_help() -> None:
    """Ensure running CLI with no arguments returns 0 and displays help."""
    exit_code = main([])
    assert exit_code == 0


def test_cli_validate_success() -> None:
    """Ensure 'validate' command passes on the official seed dataset."""
    exit_code = main(["validate", "datasets/v0.1/seed.jsonl"])
    assert exit_code == 0


def test_cli_validate_failure(tmp_path: Path) -> None:
    """Ensure 'validate' command fails on invalid dataset file."""
    bad_file = tmp_path / "bad.jsonl"
    bad_file.write_text('{"bad": "data"}\n', encoding="utf-8")
    exit_code = main(["validate", str(bad_file)])
    assert exit_code == 1


def test_cli_eval_mock_success(tmp_path: Path) -> None:
    """Ensure 'eval' command runs against mock model and produces JSON artifact."""
    out_file = tmp_path / "mock_eval_results.json"
    exit_code = main(
        [
            "eval",
            "-d",
            "datasets/v0.1/seed.jsonl",
            "-m",
            "mock-test-model",
            "-p",
            "mock",
            "-o",
            str(out_file),
        ]
    )
    assert exit_code == 0
    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_cli_eval_missing_dataset() -> None:
    """Ensure 'eval' command exits with 1 when dataset is not found."""
    exit_code = main(
        [
            "eval",
            "-d",
            "nonexistent_dataset.jsonl",
            "-m",
            "mock-model",
            "-p",
            "mock",
        ]
    )
    assert exit_code == 1


def test_cli_leaderboard_success(tmp_path: Path) -> None:
    """Ensure 'leaderboard' command parses directory and outputs table."""
    # First generate a run report in the directory
    out_file = tmp_path / "run1.json"
    main(
        [
            "eval",
            "-d",
            "datasets/v0.1/seed.jsonl",
            "-m",
            "mock-model-a",
            "-p",
            "mock",
            "-o",
            str(out_file),
        ]
    )

    exit_code = main(["leaderboard", "-r", str(tmp_path)])
    assert exit_code == 0


def test_cli_leaderboard_missing_dir() -> None:
    """Ensure 'leaderboard' command exits with 1 on non-existent directory."""
    exit_code = main(["leaderboard", "-r", "non_existent_results_dir"])
    assert exit_code == 1
