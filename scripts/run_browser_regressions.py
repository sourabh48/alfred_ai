"""Run ALFRED's Selenium-backed browser regression suite.

The normal Django test run keeps these tests skipped unless
ALFRED_RUN_BROWSER_TESTS=true. This wrapper sets the environment explicitly,
routes browser failure artifacts to artifacts/browser by default, and can fail a
CI job if the suite is skipped instead of driver-backed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_LABELS = ("tests.test_document_review_browser",)
SUMMARY_FILENAME = "browser_regression_summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "test_labels",
        nargs="*",
        default=DEFAULT_TEST_LABELS,
        help="Django test labels to run. Defaults to the Selenium browser suite.",
    )
    parser.add_argument(
        "--browser",
        choices=("Chrome", "Edge"),
        help="Limit Selenium to one browser. If omitted, Chrome is tried before Edge.",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/browser",
        help="Directory for screenshots, page HTML, metadata, and browser logs on failures.",
    )
    parser.add_argument(
        "--require-browser",
        action="store_true",
        help="Return a non-zero status if Selenium tests are skipped, useful for CI browser jobs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_dir = Path(args.artifact_dir)
    if not artifact_dir.is_absolute():
        artifact_dir = REPO_ROOT / artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["ALFRED_RUN_BROWSER_TESTS"] = "true"
    env["ALFRED_BROWSER_ARTIFACT_DIR"] = str(artifact_dir)
    if args.browser:
        env["ALFRED_BROWSER"] = args.browser

    command = [sys.executable, "manage.py", "test", *args.test_labels]
    print("Running browser regression command:")
    print(" ".join(command))
    print(f"ALFRED_RUN_BROWSER_TESTS={env['ALFRED_RUN_BROWSER_TESTS']}")
    print(f"ALFRED_BROWSER={env.get('ALFRED_BROWSER', 'Chrome then Edge')}")
    print(f"ALFRED_BROWSER_ARTIFACT_DIR={env['ALFRED_BROWSER_ARTIFACT_DIR']}")

    started_at = datetime.now(timezone.utc)
    started_perf = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output_lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        output_lines.append(line)
        print(line, end="")

    return_code = process.wait()
    output = "".join(output_lines)
    finished_at = datetime.now(timezone.utc)
    summary = build_run_summary(
        command=command,
        output=output,
        return_code=return_code,
        require_browser=args.require_browser,
        browser=args.browser or "Chrome then Edge",
        artifact_dir=artifact_dir,
        test_labels=args.test_labels,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=time.monotonic() - started_perf,
        run_browser_tests_env=env["ALFRED_RUN_BROWSER_TESTS"],
    )
    summary_path = write_summary(artifact_dir, summary)
    print(f"Browser regression summary: {summary_path}")

    if summary["runner_return_code"] == 2:
        print(
            f"Browser regression job skipped {summary['skipped_count']} Selenium test(s). "
            "Install Chrome or Edge plus matching driver support, or remove --require-browser for a soft local run."
        )
    return int(summary["runner_return_code"])


def build_run_summary(
    *,
    command: list[str],
    output: str,
    return_code: int,
    require_browser: bool,
    browser: str,
    artifact_dir: Path,
    test_labels: list[str] | tuple[str, ...],
    started_at: datetime,
    finished_at: datetime,
    duration_seconds: float,
    run_browser_tests_env: str,
) -> dict:
    skipped = skipped_count(output)
    tests_found = tests_found_count(output)
    tests_run = tests_run_count(output)
    runner_return_code = 2 if return_code == 0 and require_browser and skipped else return_code
    driver_backed_success = (
        runner_return_code == 0
        and skipped == 0
        and tests_run > 0
        and run_browser_tests_env.lower() in {"1", "true", "yes"}
    )
    if driver_backed_success:
        status = "passed"
    elif skipped:
        status = "skipped"
    else:
        status = "failed"

    return {
        "summary_version": 1,
        "status": status,
        "command": command,
        "test_labels": list(test_labels),
        "browser": browser,
        "artifact_dir": str(artifact_dir),
        "require_browser": require_browser,
        "run_browser_tests_env": run_browser_tests_env,
        "return_code": return_code,
        "runner_return_code": runner_return_code,
        "tests_found_count": tests_found,
        "tests_run_count": tests_run,
        "skipped_count": skipped,
        "driver_backed_success": driver_backed_success,
        "run_context": "ci" if os.environ.get("GITHUB_ACTIONS") == "true" else "local",
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round(duration_seconds, 3),
    }


def write_summary(artifact_dir: Path, summary: dict) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_dir / SUMMARY_FILENAME
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary_path


def skipped_count(output: str) -> int:
    match = re.search(r"skipped=(\d+)", output)
    if not match:
        return 0
    return int(match.group(1))


def tests_found_count(output: str) -> int:
    match = re.search(r"Found\s+(\d+)\s+test", output)
    if not match:
        return 0
    return int(match.group(1))


def tests_run_count(output: str) -> int:
    match = re.search(r"Ran\s+(\d+)\s+test", output)
    if not match:
        return 0
    return int(match.group(1))


if __name__ == "__main__":
    raise SystemExit(main())
