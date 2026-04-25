"""Run the BosWay Chrome browser checks and save their artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from subway.chrome_test_runner import run_chrome_test_suite


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(
        description="Run the BosWay Chrome browser verification suite.",
    )
    argument_parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="BosWay base URL to test.",
    )
    argument_parser.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible Google Chrome window instead of headless mode.",
    )
    argument_parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent.parent / "test-results"),
        help="Directory for chrome-tests.json and chrome-tests.md.",
    )
    cli_arguments = argument_parser.parse_args()

    chrome_test_run = run_chrome_test_suite(
        base_url=cli_arguments.base_url,
        headless=not cli_arguments.headed,
        output_directory=Path(cli_arguments.output_dir).expanduser(),
        project_directory=Path(__file__).resolve().parent,
        python_executable=Path(__file__).resolve().parent.parent
        / ".venv"
        / "bin"
        / "python",
    )
    failed_results = [
        result
        for result in chrome_test_run.results
        if result.status == "fail"
    ]

    print(
        "Chrome test run complete:",
        len(chrome_test_run.results),
        "executed,",
        len(failed_results),
        "failed.",
    )
    raise SystemExit(1 if failed_results else 0)
