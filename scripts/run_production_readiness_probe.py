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


def run_probe(
    *,
    proof_path: str | None = None,
    celery_ping_timeout: float = 1.0,
    ping_celery: bool = True,
    browser_summary_path: str | None = None,
    cache_traffic_proof_path: str | None = None,
) -> dict:
    ensure_django_ready()
    from alfred_ai.services.production_readiness import write_production_deployment_proof

    return write_production_deployment_proof(
        proof_path=proof_path,
        celery_ping_timeout=celery_ping_timeout,
        ping_celery=ping_celery,
        browser_summary_path=browser_summary_path,
        cache_traffic_proof_path=cache_traffic_proof_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe ALFRED production readiness and write a deployment proof JSON.")
    parser.add_argument("--proof-path", default=None, help="Output path for the production readiness proof JSON.")
    parser.add_argument("--browser-summary-path", default=None, help="Path to browser_regression_summary.ci-chrome.json.")
    parser.add_argument("--cache-traffic-proof-path", default=None, help="Path to materialized cache traffic proof JSON.")
    parser.add_argument("--celery-ping-timeout", type=float, default=1.0, help="Celery worker ping timeout in seconds.")
    parser.add_argument(
        "--skip-celery-ping",
        action="store_true",
        help="Write a rejected proof without pinging workers; useful for local diagnostics only.",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="Exit non-zero unless the generated deployment proof is accepted.",
    )
    args = parser.parse_args(argv)

    result = run_probe(
        proof_path=args.proof_path,
        celery_ping_timeout=args.celery_ping_timeout,
        ping_celery=not args.skip_celery_ping,
        browser_summary_path=args.browser_summary_path,
        cache_traffic_proof_path=args.cache_traffic_proof_path,
    )
    validation = dict(result.get("validation") or {})
    output = {
        "proof_path": result.get("proof_path", ""),
        "accepted": bool(validation.get("accepted")),
        "state": validation.get("state", ""),
        "summary": validation.get("summary", ""),
        "blockers": validation.get("blockers", []),
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    if args.require_ready and not validation.get("accepted"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
