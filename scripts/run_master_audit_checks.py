"""Run bounded public-source diagnostics in disposable storage; never starts the live runtime."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid

ROOT = Path(__file__).resolve().parents[1]
LABELS = (
    "tests.test_financial_baseline_alignment", "tests.test_family_account_links",
    "tests.test_hybrid_intelligence", "tests.test_document_grounding_acceptance",
    "tests.test_intelligence_currency", "tests.test_api_session_security", "tests.test_tax_policy",
)


def isolated_environment(directory):
    directory = Path(directory).resolve()
    allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE",
               "LOCALAPPDATA", "APPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMDATA",
               "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE"}
    result = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    result.update(ALFRED_LOCAL_RUNTIME="true", ALFRED_AUTO_TRAIN_ON_STARTUP="false",
                  ALFRED_DATA_DIR=str(directory), ALFRED_LOCAL_ENV_FILE=str(directory / "absent.env"),
                  ALFRED_REGISTRY_PATH=str(directory / "registry"),
                  ALFRED_MEMORY_CLOUD_AUTHORIZED="false", ALFRED_MEMORY_SYNC_PROVIDER="",
                  ALFRED_MEMORY_OPENAI_AUTHORIZED="false", ALFRED_RUN_BROWSER_TESTS="false",
                  DJANGO_SECRET_KEY=uuid.uuid4().hex,
                  DATABASE_URL="sqlite:///" + (directory / "db.sqlite3").as_posix(),
                  CACHE_BACKEND="django.core.cache.backends.locmem.LocMemCache",
                  CACHE_LOCATION="audit-synthetic", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return result


def main():
    output = ROOT / "artifacts/audit/master-audit-inventory-20261015"
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with TemporaryDirectory(prefix="alfred-public-audit-") as directory:
        env = isolated_environment(directory)
        for name, args in (("system", ("check",)), ("migration", ("makemigrations", "--check", "--dry-run")),
                           ("focused", ("test", *LABELS, "--noinput"))):
            try:
                run = subprocess.run([sys.executable, "-B", "manage.py", *args], cwd=ROOT, env=env,
                                     capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
            except subprocess.TimeoutExpired:
                results.append({"gate": name, "status": "FAIL", "reason": "timeout"})
                continue
            combined = run.stdout + "\n" + run.stderr
            counts = re.findall(r"Ran (\d+) tests? in ([\d.]+)s", combined)
            skipped = re.findall(r"skipped=(\d+)", combined)
            safe = [line.strip() for line in combined.splitlines() if re.fullmatch(
                r"Ran \d+ tests? in [\d.]+s|OK(?: \(skipped=\d+\))?|FAILED \([\w=, ]+\)|"
                r"Found \d+ test\(s\)\.|(?:FAIL|ERROR): test_[\w]+ \([\w.]+\)|"
                r"System check identified no issues \(0 silenced\)\.|No changes detected", line.strip())]
            (output / (name + "-safe.log")).write_text("\n".join(safe) + "\nOther diagnostics omitted.\n", encoding="utf-8")
            results.append({"gate": name, "status": "PASS" if run.returncode == 0 else "FAIL",
                            "exit": run.returncode, "tests": int(counts[-1][0]) if counts else 0,
                            "seconds": float(counts[-1][1]) if counts else None,
                            "skips": int(skipped[-1]) if skipped else 0})
    receipt = {"baseline": "3932f391aa4eed7b3200ad3b034f7991435e01e4", "labels": LABELS,
               "results": results, "scope": "synthetic_disposable_database_no_real_provider_calls"}
    (output / "focused-checks.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 1 if any(row["status"] != "PASS" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
