"""Finish a continuous scheduled-work observation, retaining interrupted attempts."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from alfred_native import InstanceLock, write_json
from scripts.observe_native_runtime import observation_status, run_observation


def required_hours(now=None):
    """Cover the next real UTC maintenance cycles and at least ten hours."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    deadlines = []
    for hour, minute in ((2, 15), (3, 0)):
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        deadlines.append(candidate)
    refresh = now.replace(hour=(now.hour // 6) * 6, minute=0, second=0, microsecond=0)
    deadlines.append(refresh + timedelta(hours=6))
    finish = max(deadlines) + timedelta(minutes=30)
    return max(10.0, (finish - now).total_seconds() / 3600)


def load_manifest(evidence):
    path = evidence / "current.json"
    if not path.exists():
        return {"attempts": [], "passed": False, "status": "not_started"}
    return json.loads(path.read_text(encoding="utf-8"))


def latest_status(evidence):
    manifest = load_manifest(evidence)
    if not manifest.get("report"):
        return manifest
    report = Path(manifest["report"]).resolve()
    if not report.is_relative_to(evidence.resolve()):
        raise ValueError("Observation report is outside its evidence folder")
    if not report.exists():
        return {**manifest, "status": "interrupted", "passed": False,
                "reason": "The attempt did not produce an observation report."}
    result = observation_status(json.loads(report.read_text(encoding="utf-8")))
    return {**manifest, **result}


def supervise(data, executable, evidence, *, retry_failed=False):
    evidence.mkdir(parents=True, exist_ok=True)
    stop_file = evidence / "stop.requested"
    while not stop_file.exists():
        manifest = load_manifest(evidence)
        previous = latest_status(evidence)
        if previous.get("passed"):
            print("Continuous scheduled-work observation already passed.", flush=True)
            return 0
        if previous.get("status") == "finished" and not retry_failed:
            print("The completed attempt failed; inspect its jobs and health before retrying.", flush=True)
            return 1
        # The exclusive supervisor lock is already held. A previous active flag
        # therefore belongs to an observer that exited, even if its last sample
        # is still recent enough to look fresh.
        if previous.get("status") in ("starting", "observing"):
            previous = {**previous, "status": "interrupted", "passed": False}
        if manifest.get("report"):
            manifest["previous_attempt"] = {
                "report": manifest["report"], "status": previous.get("status"),
                "passed": previous.get("passed", False),
            }
        # The launcher is idempotent and keeps the existing local data folder.
        startup = subprocess.run(
            [str(executable), "start", "--data-dir", str(data), "--no-browser"],
            cwd=data, capture_output=True, text=True, errors="replace", timeout=240,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if startup.returncode:
            raise RuntimeError("ALFRED could not start: " + startup.stderr[-1000:])
        if stop_file.exists():
            return 3
        now = datetime.now(timezone.utc)
        hours = required_hours(now)
        report = evidence / (now.strftime("attempt-%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8] + ".json")
        manifest.update(
            report=str(report), status="starting", passed=False, supervisor_pid=os.getpid(),
            expected_finish=(now + timedelta(hours=hours)).isoformat(),
        )
        manifest.setdefault("attempts", []).append(str(report))
        write_json(evidence / "current.json", manifest)
        print(json.dumps({"report": str(report), "expected_finish": manifest["expected_finish"]}), flush=True)
        result = run_observation(data, hours, 60, report, restart_on_gap=True, stop_file=stop_file)
        outcome = latest_status(evidence)
        manifest.update(status=outcome["status"], passed=outcome["passed"])
        write_json(evidence / "current.json", manifest)
        if result != 2:
            return result
        # A sleep gap cannot be repaired by combining samples. Preserve it and
        # observe a new full window, including the next daily schedules.
        print("Interrupted attempt retained; beginning a fresh continuous window.", flush=True)
    return 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--retry-failed", action="store_true", help="Retry a completed failed attempt after its cause has been addressed")
    args = parser.parse_args()
    data, evidence = args.data_dir.resolve(), args.evidence_dir.resolve()
    if args.status:
        status = latest_status(evidence)
        print(json.dumps(status, indent=2))
        return 0 if status.get("passed") else 1
    if not args.executable or not args.executable.is_file():
        parser.error("Select an existing packaged ALFRED.exe")
    try:
        lock = InstanceLock(data, "observation-supervisor.lock")
        lock.__enter__()
    except OSError:
        print("Another observation supervisor owns this data folder.", flush=True)
        return 4
    try:
        return supervise(data, args.executable.resolve(), evidence, retry_failed=args.retry_failed)
    finally:
        lock.__exit__()


if __name__ == "__main__":
    raise SystemExit(main())
