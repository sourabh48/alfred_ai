"""Compare private pre/post-boot manifests without disclosing row contents."""
import argparse
import datetime
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--boot-time", required=True, help="Actual Windows LastBootUpTime, with timezone")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    before, after = [json.loads(path.read_text(encoding="utf-8")) for path in (args.before, args.after)]
    boot = datetime.datetime.fromisoformat(args.boot_time)
    parse_stamp = lambda value: datetime.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
    actual_boot_between_snapshots = parse_stamp(before["created_at"]) < boot < parse_stamp(after["created_at"])
    financial = {name: after["tables"].get(name) == value for name, value in before["tables"].items()
                 if name.startswith(("expenses_", "budgets_", "loans_", "investments_"))}
    uploads = {name: after["files"].get(name) == value for name, value in before["files"].items()
               if name.startswith("media/")}
    report = {
        "actual_boot_between_snapshots": actual_boot_between_snapshots, "windows_boot_time": args.boot_time,
        "financial_tables": financial, "uploaded_files_checked": len(uploads),
        "uploaded_files_unchanged": sum(uploads.values()),
        "user_count_before": before["tables"]["users_user"]["rows"],
        "user_count_after": after["tables"]["users_user"]["rows"],
        "before_backup": before["backup"], "after_backup": after["backup"],
        "scope": "Existing data retained across the observed host reboot; manual native relaunch is separate from automatic startup or a clean-PC test.",
        "passed": bool(actual_boot_between_snapshots and financial and uploads
                       and all(financial.values()) and all(uploads.values())
                       and before["tables"]["users_user"]["rows"] == after["tables"]["users_user"]["rows"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
