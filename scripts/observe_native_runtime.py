"""Record a real elapsed-time soak; never treat a manual task call as overnight proof."""
import argparse
import atexit
import datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alfred_native import read_state, write_json


REQUIRED = ("native_intelligence_refresh", "native_intelligence_cleanup", "native_nightly_training")


def snapshot(data, since):
    database = data / "artifacts" / "native" / "jobs.sqlite3"
    if not database.exists():
        return [], "Queue database missing"
    try:
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=10) as connection:
            rows = connection.execute(
                "SELECT name, started, finished, outcome, summary FROM native_history "
                "WHERE started>=? AND name NOT LIKE '%heartbeat' ORDER BY started", (since,)).fetchall()
        return [{"task": name, "started": start, "finished": end, "outcome": outcome,
                 "summary": json.loads(summary)} for name, start, end, outcome, summary in rows], None
    except sqlite3.Error as error:
        return [], type(error).__name__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--hours", type=float, default=8)
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--keep-awake", action="store_true", help="Prevent automatic Windows sleep during this observation")
    args = parser.parse_args()
    if args.hours <= 0 or args.interval < 1:
        parser.error("hours must be positive; interval must be at least one second")
    if args.keep_awake and os.name == "nt":
        import ctypes
        set_execution_state = ctypes.windll.kernel32.SetThreadExecutionState
        if not set_execution_state(0x80000001):  # CONTINUOUS | SYSTEM_REQUIRED
            raise RuntimeError("Windows could not keep this observation awake")
        atexit.register(set_execution_state, 0x80000000)
    data = args.data_dir.resolve()
    started = time.time()
    report = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "start_timestamp": started, "required_hours": args.hours, "samples": [], "passed": False}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while True:
        state = read_state(data)
        healthy = False
        try:
            with opener.open(f"http://127.0.0.1:{state.get('port', 8000)}/health/native/", timeout=10) as response:
                health = json.load(response)
            healthy = health.get("status") == "ok" and health.get("instance") == state.get("instance")
        except (OSError, ValueError):
            pass
        now = time.time()
        report["samples"].append({"time": now, "healthy": healthy, "instance": state.get("instance")})
        report["jobs"], report["history_error"] = snapshot(data, started)
        report["elapsed_hours"] = round((now - started) / 3600, 4)
        report["pending_schedules"] = [name for name in REQUIRED if not any(
            job["task"].endswith("." + name) and job["outcome"] == "complete" for job in report["jobs"])]
        report["failed_job_count"] = sum(job["outcome"] in ("error", "interrupted_needs_review")
                                          or job["summary"].get("failed_count", 0) > 0 for job in report["jobs"])
        gap = any(b["time"] - a["time"] > max(180, args.interval * 3)
                  for a, b in zip(report["samples"], report["samples"][1:]))
        report["sampling_gap"] = gap
        finished = now - started >= args.hours * 3600
        report["status"] = "finished" if finished else "observing"
        report["passed"] = (finished and not gap and not report["pending_schedules"]
                            and not report["history_error"] and not report["failed_job_count"]
                            and all(item["healthy"] for item in report["samples"]))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.report.resolve(), report)
        if finished:
            print(json.dumps({key: report[key] for key in ("status", "passed", "pending_schedules", "elapsed_hours")}))
            return 0 if report["passed"] else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
