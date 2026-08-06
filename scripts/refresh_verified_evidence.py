from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("ALFRED_LOCAL_RUNTIME", "true")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alfred_ai.settings")


def ensure_django_ready() -> None:
    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()


def run_refresh(*, batch_size: int | None = None, proof_path: str | None = None) -> dict:
    ensure_django_ready()
    from apps.integrations.services import verified_intelligence

    return verified_intelligence.refresh_due_records(
        batch_size=batch_size,
        write_proof=True,
        proof_path=proof_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh verified external evidence and write a proof artifact.")
    parser.add_argument("--batch-size", type=int, default=None, help="Maximum number of due evidence records to refresh.")
    parser.add_argument("--proof-path", default=None, help="Optional output path for the evidence refresh proof JSON.")
    parser.add_argument(
        "--require-healthy",
        action="store_true",
        help="Exit non-zero unless the generated proof is accepted.",
    )
    args = parser.parse_args(argv)

    result = run_refresh(batch_size=args.batch_size, proof_path=args.proof_path)
    proof = dict(result.get("refresh_proof") or {})
    validation = dict(proof.get("validation") or {})
    output = {
        "processed": result.get("processed", 0),
        "refreshed": result.get("refreshed", 0),
        "skipped": result.get("skipped", 0),
        "failed": result.get("failed", 0),
        "watchlist_before": result.get("watchlist_before", 0),
        "watchlist_after": result.get("watchlist_after", 0),
        "proof_path": proof.get("proof_path", ""),
        "proof_accepted": bool(validation.get("accepted")),
        "proof_summary": validation.get("summary", ""),
        "proof_blockers": validation.get("blockers", []),
    }
    print(json.dumps(output, indent=2, sort_keys=True, default=str))
    if args.require_healthy and not validation.get("accepted"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
