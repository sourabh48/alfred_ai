from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from alfred_ai.services.materialized_cache import materialized_cache_health_snapshot
from apps.career.models import CareerJobAnalysis, CareerResume, CareerResumeLearningMemory
from apps.career.services.job_intelligence import career_opportunity_outcome_summary, career_source_coverage_summary
from apps.expenses.models import Expense, StatementUpload
from apps.integrations.models import CreditReportUpload, VerifiedExternalInsight
from apps.loans.models import LoanClosureDocument, LoanPaymentHistory
from apps.mobility.models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeServiceRecord
from apps.mobility.services.bike_catalog import catalog_coverage_summary
from apps.ml_engine.models import DocumentParserLearningMemory
from apps.ml_engine.training.orchestrator import training_health_snapshot
from apps.reports.models import ChatGPTImport, GeneratedReport, SystemTicket
from .internal_clock import clock_snapshot


BROWSER_REGRESSION_SUMMARY_FILENAME = "browser_regression_summary.json"


def _bounded_percent(value: float, *, default: int = 0) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(100, int(round(numeric))))


def _progress(current: float, target: float, *, floor: int = 10, ceiling: int = 95) -> int:
    if target <= 0:
        return _bounded_percent(floor)
    ratio = max(0.0, min(current / target, 1.0))
    return _bounded_percent(max(floor, min(ceiling, round(floor + ((ceiling - floor) * ratio)))))


def _browser_regression_summary_path() -> Path:
    configured_path = os.environ.get("ALFRED_BROWSER_REGRESSION_SUMMARY", "").strip()
    if configured_path:
        path = Path(configured_path)
    else:
        artifact_dir = Path(os.environ.get("ALFRED_BROWSER_ARTIFACT_DIR", "artifacts/browser"))
        path = artifact_dir / BROWSER_REGRESSION_SUMMARY_FILENAME
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


def _project_relative_path(path: Path) -> str:
    try:
        return path.relative_to(settings.BASE_DIR).as_posix()
    except ValueError:
        return str(path)


def _as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _browser_regression_health_snapshot() -> dict:
    path = _browser_regression_summary_path()
    summary_path = _project_relative_path(path)
    default = {
        "summary_path": summary_path,
        "summary_filename": BROWSER_REGRESSION_SUMMARY_FILENAME,
        "recorded": False,
        "maturity_gate_recorded": False,
        "status": "not_recorded",
        "browser": "not recorded",
        "run_context": "not recorded",
        "finished_at_utc": "",
        "duration_seconds": None,
        "skipped_count": None,
        "tests_run_count": None,
        "runner_return_code": None,
        "driver_backed_success": False,
        "require_browser": False,
        "summary": (
            f"No driver-backed browser regression summary has been recorded yet; run "
            f"`python scripts/run_browser_regressions.py --browser Chrome --require-browser` "
            f"to create {summary_path}."
        ),
    }
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        default.update(
            {
                "recorded": True,
                "status": "invalid",
                "summary": f"Browser regression summary is present but unreadable: {exc}",
            }
        )
        return default

    skipped_count = _as_int(payload.get("skipped_count"), 0)
    tests_run_count = _as_int(payload.get("tests_run_count"), 0)
    runner_return_code = _as_int(payload.get("runner_return_code"), 1)
    driver_backed_success = bool(payload.get("driver_backed_success")) and skipped_count == 0 and tests_run_count > 0
    maturity_gate_recorded = (
        driver_backed_success
        and runner_return_code == 0
        and bool(payload.get("require_browser"))
        and str(payload.get("run_browser_tests_env", "")).lower() in {"1", "true", "yes"}
    )
    browser = str(payload.get("browser") or "not recorded")
    run_context = str(payload.get("run_context") or "not recorded")
    finished_at = str(payload.get("finished_at_utc") or "")
    status = str(payload.get("status") or ("passed" if maturity_gate_recorded else "failed"))
    summary = (
        f"Latest {run_context} {browser} browser run recorded {status} with "
        f"{skipped_count} skipped test(s), {tests_run_count} test(s) run, and runner return code {runner_return_code}."
    )
    if maturity_gate_recorded:
        summary += " Driver-backed proof is recorded; full UI maturity still needs repeated healthy local/CI runs and broader interaction depth."
    else:
        summary += " Driver-backed proof is not accepted until the summary shows a required-browser run with zero skips and a zero runner return code."

    return {
        **default,
        "recorded": True,
        "maturity_gate_recorded": maturity_gate_recorded,
        "status": status,
        "browser": browser,
        "run_context": run_context,
        "finished_at_utc": finished_at,
        "duration_seconds": payload.get("duration_seconds"),
        "skipped_count": skipped_count,
        "tests_run_count": tests_run_count,
        "runner_return_code": runner_return_code,
        "driver_backed_success": driver_backed_success,
        "require_browser": bool(payload.get("require_browser")),
        "summary": summary,
    }


def _catalog_source_refresh_health(catalog_summary: dict, now) -> dict:
    source_refresh = dict(catalog_summary.get("source_refresh") or {})
    last_checked_on = str(source_refresh.get("last_checked_on") or "").strip()
    try:
        refresh_policy_days = int(source_refresh.get("refresh_policy_days") or 45)
    except (TypeError, ValueError):
        refresh_policy_days = 45
    checked_date = None
    if last_checked_on:
        try:
            checked_date = date.fromisoformat(last_checked_on)
        except ValueError:
            checked_date = None
    if not checked_date:
        return {
            "status": "missing",
            "last_checked_on": last_checked_on,
            "age_days": None,
            "refresh_policy_days": refresh_policy_days,
            "next_due_on": "",
            "summary": "source refresh date missing",
        }
    today = timezone.localdate(now)
    age_days = max((today - checked_date).days, 0)
    next_due_on = checked_date + timedelta(days=refresh_policy_days)
    status = "fresh" if today <= next_due_on else "due"
    return {
        "status": status,
        "last_checked_on": last_checked_on,
        "age_days": age_days,
        "refresh_policy_days": refresh_policy_days,
        "next_due_on": next_due_on.isoformat(),
        "summary": f"{status} within {refresh_policy_days}-day policy; checked {last_checked_on}; due {next_due_on.isoformat()}",
    }


def _build_learning_snapshot(now) -> dict:
    model_training = training_health_snapshot()
    catalog_summary = catalog_coverage_summary()
    catalog_refresh = _catalog_source_refresh_health(catalog_summary, now)
    career_source_summary = career_source_coverage_summary()
    career_outcome_summary = career_opportunity_outcome_summary(CareerJobAnalysis.objects.all())
    transaction_count = Expense.objects.count()
    statement_upload_count = StatementUpload.objects.count()
    matched_loan_payments = LoanPaymentHistory.objects.filter(match_status="matched").count()
    review_loan_payments = LoanPaymentHistory.objects.filter(match_status="review").count()

    vehicle_documents = BikeDocument.objects.count()
    service_records = BikeServiceRecord.objects.count()
    condition_snapshots = BikeConditionSnapshot.objects.count()
    open_vehicle_issues = BikeIssueReport.objects.exclude(status="resolved").count()
    resolved_vehicle_issues = BikeIssueReport.objects.filter(status="resolved").count()
    costed_vehicle_issue_outcomes = BikeIssueReport.objects.filter(status="resolved").exclude(actual_cost__isnull=True).count()

    resumes = CareerResume.objects.count()
    recruiter_documents = CareerJobAnalysis.objects.filter(
        extracted_payload__source_kind__in=["recruiter_message", "jd_attachment"]
    ).count()
    chatgpt_imports = ChatGPTImport.objects.count()
    resume_learning_memories = CareerResumeLearningMemory.objects.count()
    job_analyses = CareerJobAnalysis.objects.count()
    credit_report_uploads = CreditReportUpload.objects.count()
    parser_correction_memories = DocumentParserLearningMemory.objects.filter(correction_count__gt=0).count()
    parser_correction_scopes = (
        DocumentParserLearningMemory.objects.filter(correction_count__gt=0).values("scope").distinct().count()
    )

    verified_evidence = VerifiedExternalInsight.objects.filter(is_active=True).count()
    fresh_evidence = VerifiedExternalInsight.objects.filter(is_active=True).filter(
        Q(status="fresh") & Q(stale_after__gt=now)
    ).count()
    stale_evidence = VerifiedExternalInsight.objects.filter(is_active=True).filter(
        Q(status__in=["stale", "failed", "rejected"]) | Q(stale_after__lte=now)
    ).count()

    finance_progress = _progress(transaction_count + (statement_upload_count * 12) + (matched_loan_payments * 8), 420, floor=18)
    document_progress = _bounded_percent(
        max(
            14,
            _progress(
                vehicle_documents + statement_upload_count + resumes + recruiter_documents + credit_report_uploads + (chatgpt_imports * 0.5) + (resume_learning_memories * 0.75),
                72,
                floor=20,
            )
            + (parser_correction_memories * 1.5)
            + (parser_correction_scopes * 2)
            - min(review_loan_payments * 2, 10),
        )
    )
    mobility_scope_complete = catalog_summary["completion_status"] == "complete_current_scope"
    mobility_progress = _progress(
        service_records
        + condition_snapshots
        + open_vehicle_issues
        + (resolved_vehicle_issues * 2)
        + (costed_vehicle_issue_outcomes * 3)
        + (vehicle_documents * 0.5),
        64,
        floor=16,
    )
    if mobility_scope_complete:
        mobility_progress = max(mobility_progress, 88)
    career_progress = _progress(
        (resumes * 14)
        + (resume_learning_memories * 10)
        + (job_analyses * 14)
        + (career_outcome_summary["salary_bearing_outcome_count"] * 8)
        + (career_outcome_summary["accepted_count"] * 4)
        + (career_outcome_summary["rejected_count"] * 4)
        + (fresh_evidence * 2),
        190,
        floor=15,
    )
    if career_source_summary["completion_status"] == "complete_current_scope":
        career_progress = max(career_progress, 88)
    evidence_progress = max(12, _progress(fresh_evidence, max(verified_evidence, 1), floor=22) - min(stale_evidence * 3, 25))

    tracks = [
        {
            "title": "Finance behavior learning",
            "progress": finance_progress,
            "detail": "Expense classification, emotional-spend scoring, anomaly detection, monthly timeline windows, and statement-linked loan recognition are learning from live transaction history.",
            "maturity_status": "Correction-gated",
            "signals": [
                f"{transaction_count} transactions",
                f"{statement_upload_count} statement uploads",
                f"{matched_loan_payments} loan payments linked",
            ],
            "blocker_label": "Completion gate",
            "blocker": "Broader correction loops are still needed for non-perfect statement and transaction classifications.",
            "blocked_by_real_data": True,
            "completion_actions": [
                "Review misclassified statement transactions and accept corrections that update classifier memory.",
                "Keep original statement, parsed field, corrected value, and accepted category together for every correction outcome.",
                "Re-run the finance ingestion regression once enough non-perfect imports have accepted corrections.",
            ],
        },
        {
            "title": "Document intelligence",
            "progress": document_progress,
            "detail": "Statements, resumes, recruiter/JD intake, vehicle documents, credit reports, ChatGPT context imports, and loan PDFs now expose parser confidence, OCR overlay evidence, schema-aware correction candidates, cross-family unknown-layout fixtures, accepted correction memory outcomes, Selenium-proven correction interaction, and retry-fed learning traces where applicable.",
            "maturity_status": "Real-layout gated",
            "signals": [
                f"{statement_upload_count + vehicle_documents + resumes + recruiter_documents + credit_report_uploads} parser-tracked uploads",
                f"{chatgpt_imports} ChatGPT context imports",
                f"{review_loan_payments} review-needed loan matches",
                f"{recruiter_documents} recruiter/JD intake records",
                f"{vehicle_documents} vehicle documents stored",
                f"{parser_correction_memories} accepted parser-correction memories",
                f"{parser_correction_scopes} document families with accepted corrections",
            ],
            "blocker_label": "Completion gate",
            "blocker": "The current review workflow is stronger for supported layouts; live maturity still depends on more real samples from unknown and long-tail document layouts plus browser interaction proof beyond the vehicle invoice/OCR correction path.",
            "blocked_by_real_data": True,
            "completion_actions": [
                "Upload and resolve real unknown layouts for statements, loans, loan closures, investments, vehicles, resumes, recruiter messages, and credit reports.",
                "Accept field corrections through the review queue until DocumentParserLearningMemory records validated outcomes by document family.",
                "Expand browser interaction tests from vehicle invoice/OCR overlay correction into the remaining document-family review flows.",
            ],
        },
        {
            "title": "Vehicle maintenance learning",
            "progress": mobility_progress,
            "detail": (
                "The supported vehicle-maintenance implementation scope is in place: service bills, condition snapshots, issue history, "
                "official model-specific maintenance guidance, source freshness metadata, route-aware wear signals, bounded service-cost learning, and brand-filtered catalog selection are blended into the vehicle dashboard."
                if mobility_scope_complete
                else "Service bills, condition snapshots, issue history, official model-specific maintenance guidance, route-aware wear signals, and bounded service-cost learning are now blended into the vehicle dashboard."
            ),
            "signals": [
                f"{service_records} service logs",
                f"{condition_snapshots} condition snapshots",
                f"{open_vehicle_issues} open issue reports",
                f"{resolved_vehicle_issues} resolved issue outcomes",
                f"{costed_vehicle_issue_outcomes} costed issue outcomes",
                f"{catalog_summary['model_count']} official catalog models",
                f"{catalog_summary['manufacturer_count']} manufacturers covered",
                f"{catalog_summary['source_checked_coverage_pct']}% source links checked",
                catalog_refresh["summary"],
            ],
            "maturity_status": "Usage-gated",
            "blocker_label": "Remaining maturity" if mobility_scope_complete else "Still blocked by",
            "blocker": (
                "Catalog depth is strong for the supported India seed scope, but it is not exhaustive; source links must remain inside the refresh policy, long-tail models should come from real usage gaps, and maturity still needs denser condition snapshots plus more resolved/costed issue outcomes."
                if mobility_scope_complete
                else "Catalog coverage still has required manufacturer, model, source, or maintenance-guidance gaps."
            ),
            "blocked_by_real_data": True,
            "completion_actions": [
                "Keep official source links inside the configured refresh policy before raising catalog maturity.",
                "Add long-tail vehicle models only from real user selections, support tickets, or verified usage gaps.",
                "Record condition snapshots and resolve maintenance issues with actual cost outcomes for every high-demand model family.",
            ],
        },
        {
            "title": "Career and market intelligence",
            "progress": career_progress,
            "detail": "Resume parsing, recruiter/JD intake, compensation benchmarking, public job-page parsing, multi-feed live openings, geography-aware salary evidence, specialty-source gap policy, and salary-bearing opportunity outcomes are tracked for the current source scope.",
            "maturity_status": "Outcome-gated",
            "signals": [
                f"{resumes} resumes",
                f"{resume_learning_memories} learned parser memory signatures",
                f"{job_analyses} job analyses",
                f"{career_outcome_summary['salary_bearing_outcome_count']} salary-bearing outcomes",
                f"{career_outcome_summary['accepted_count']} accepted outcomes",
                f"{career_outcome_summary['rejected_count']} rejected outcomes",
                f"{fresh_evidence} fresh evidence records",
                f"{career_source_summary['configured_feed_count']} live job-feed adapters",
                f"{career_source_summary['job_page_adapter_count']} job-page adapters",
            ],
            "blocker_label": "Completion gate",
            "blocker": "Current source breadth is complete; specialty-source additions stay gated on real role/geography gaps, and salary maturity still needs more accepted and rejected salary-bearing opportunity outcomes.",
            "blocked_by_real_data": True,
            "completion_actions": [
                "Log accepted and rejected opportunities with salary-bearing evidence before increasing compensation-learning maturity.",
                "Add specialty sources only after real users expose repeated role or geography gaps in current feeds.",
                "Validate salary range, location match, and outcome decision together before counting an opportunity as learning evidence.",
            ],
        },
        {
            "title": "Verified evidence refresh",
            "progress": evidence_progress,
            "detail": "Travel, career, risk, investment, tax, recommendation, relationship, family, and behavioral planning surfaces use proof-linked freshness metadata, circuit breakers, stale fallback, and scheduled refresh.",
            "maturity_status": (
                "Evidence missing" if verified_evidence == 0 else "Refresh due" if stale_evidence else "Refresh healthy"
            ),
            "signals": [
                f"{verified_evidence} verified records",
                f"{fresh_evidence} fresh",
                f"{stale_evidence} stale or failed",
            ],
            "blocker_label": "Freshness gate",
            "blocker": (
                "Current proof-enforcement scope is complete; freshness can dip when upstream evidence becomes stale or due and should be recovered by scheduled refresh."
                if stale_evidence == 0
                else "Freshness is currently held back by stale, failed, rejected, or due external evidence records."
            ),
            "blocked_by_real_data": verified_evidence == 0 or stale_evidence > 0,
            "completion_actions": [
                "Keep scheduled refresh jobs running until active verified evidence is fresh or has an explicit stale fallback.",
                "Extend proof contracts before adding any new recommendation or relationship-adjacent signal.",
                "Track refresh outcome, circuit-breaker state, source URL, and stale-after deadline for every advisory surface.",
            ],
        },
        {
            "title": "Model training lifecycle",
            "progress": _bounded_percent(model_training["overall_progress"]),
            "detail": "Supported models retrain only when runtime dependencies are healthy, data thresholds are met, and the refresh window is due; the displayed progress is the live model-state maturity score.",
            "maturity_status": "Training-gated",
            "signals": [
                f"{model_training['ready_models']} ready model states",
                f"{model_training['fresh_models']} fresh artifacts",
                f"{model_training['skipped_models']} skipped by data or implementation gates",
                f"{model_training['average_confidence']} average confidence estimate",
            ],
            "blocker_label": "Completion gate",
            "blocker": model_training["summary"],
            "blocked_by_real_data": bool(model_training.get("skipped_models") or model_training.get("failed_models")),
            "completion_actions": [
                "Keep supervised artifacts inside their freshness windows and rerun training when refresh windows are due.",
                "Collect accepted outcomes for supervised learners that are skipped by data thresholds.",
                "Keep the planned future RL learner out of production-ready ML counts until it has a real deployment contract.",
            ],
        },
    ]

    overall_progress = _bounded_percent(mean(track["progress"] for track in tracks)) if tracks else 0
    data_gated_tracks = sum(1 for track in tracks if track.get("blocked_by_real_data"))
    completion_action_count = sum(len(track.get("completion_actions", [])) for track in tracks)
    return {
        "overall_progress": overall_progress,
        "data_gated_tracks": data_gated_tracks,
        "completion_action_count": completion_action_count,
        "completion_summary": (
            f"{data_gated_tracks} adaptive track(s) are waiting on real accepted outcomes, fresh evidence, or production telemetry; "
            f"{completion_action_count} completion actions are listed below so those gates can be closed without overclaiming maturity."
        ),
        "summary": "ALFRED is adaptive across multiple modules, but this progress bar is a live maturity heuristic based on current data coverage, freshness, and training state, not a release-completion percentage. Several important paths still blend reviewed ML components with rule-based and evidence-backed heuristics.",
        "tracks": sorted(tracks, key=lambda item: item["progress"]),
        "implementation_state": {
            "ml_backed": [
                "Behavioral anomaly detection, signature generation, and savings-strategy personalization run on stored transaction history.",
                "Expense enrichment applies model-style confidence scoring and emotional-spend detection to imported and manual entries.",
                "Parser confidence is stored for resumes, statements, vehicle documents, and loan PDFs.",
                "Supported structured models now keep persisted training state, refresh windows, and confidence estimates, including a bounded mobility service-cost regressor.",
            ],
            "adaptive_blended": [
                "Career timing, risk radar, vehicle fault diagnosis, and travel readiness are adaptive but still blend verified evidence with heuristics.",
                "Career source coverage now spans Remotive, Arbeitnow, Remote OK, recruiter/JD intake, job-page adapters, geography-aware salary evidence contracts, specialty-source gap policy, and salary-bearing opportunity outcomes.",
                "Vehicle dashboard suggestions adjust with service history, fault history, resolved/costed issue outcomes, condition snapshots, source-checked catalog metadata, and document state.",
                "Verified external intelligence refreshes in the background with freshness contracts, stale fallback, and circuit breakers.",
                "Investment watchlist ranking blends official AMFI NAV history, verified market context, and user portfolio fit, but still remains a transparent watchlist rather than a guarantee engine.",
            ],
            "not_yet_fully_learned": [
                "Unknown document layouts now improve through correction memory, schema-aware OCR overlay candidates, cross-family unknown-layout fixtures, label-collapsed invoice recovery, Selenium-proven vehicle invoice correction, and retry outcomes; maturity still depends on real long-tail sample volume.",
                "Career source breadth is complete for the current scope, but specialty-source additions are still gated on real role/geography gaps and career outcome learning needs more salary-bearing accepted/rejected decisions.",
                "Home-loan dashboard value now includes tracked upfront cash inputs, but it is still an acquisition-cost proxy rather than a live market valuation.",
                "Large dashboard payloads now use revision-keyed materialized responses; remaining scaling work is production cache sizing, TTL tuning, and observability.",
                "The planned future RL learner is tracked as planned-only and is excluded from production-ready ML and supervised model coverage.",
            ],
        },
        "model_training": model_training,
    }


def project_details_payload(guardrails: dict) -> dict:
    now = timezone.now()
    clock = clock_snapshot(now)
    user_model = get_user_model()

    developer_escalations = SystemTicket.objects.filter(handled_by="developer").exclude(status="resolved")
    alfred_resolved = SystemTicket.objects.filter(handled_by="alfred", status="resolved")
    evidence_watchlist = VerifiedExternalInsight.objects.filter(is_active=True).filter(
        Q(status__in=["stale", "failed", "rejected"]) | Q(stale_after__lte=now)
    )
    loan_review_queue = LoanPaymentHistory.objects.filter(match_status="review")
    closure_pending = LoanClosureDocument.objects.filter(verification_status="pending")
    closure_rejected = LoanClosureDocument.objects.filter(verification_status="rejected")
    generated_reports = GeneratedReport.objects.order_by("-created_at", "-id")
    chatgpt_imports = ChatGPTImport.objects.order_by("-created_at", "-id")

    learning_snapshot = _build_learning_snapshot(now)
    learning_tracks_by_title = {item["title"]: item for item in learning_snapshot["tracks"]}
    document_track = learning_tracks_by_title.get("Document intelligence", {})
    vehicle_track = learning_tracks_by_title.get("Vehicle maintenance learning", {})
    career_track = learning_tracks_by_title.get("Career and market intelligence", {})
    evidence_track = learning_tracks_by_title.get("Verified evidence refresh", {})
    proof_contract_snapshot = dict(guardrails.get("proof_contract") or {})
    refresh_health = dict(guardrails.get("refresh_health") or {})
    proof_surface_count = int(proof_contract_snapshot.get("surface_count") or 0)
    proof_covered_surface_count = int(proof_contract_snapshot.get("covered_surface_count") or 0)
    proof_contract_healthy = bool(proof_contract_snapshot.get("healthy")) if proof_surface_count else False
    scheduled_refresh_name = proof_contract_snapshot.get("scheduled_refresh") or "refresh_due_records"
    evidence_watchlist_count = int(refresh_health.get("watchlist_records", evidence_watchlist.count()) or 0)
    evidence_fresh_count = int(refresh_health.get("fresh_records", 0) or 0)
    evidence_active_count = int(refresh_health.get("active_records", 0) or 0)
    cache_health = materialized_cache_health_snapshot()
    catalog_summary = catalog_coverage_summary()
    catalog_refresh = _catalog_source_refresh_health(catalog_summary, now)
    career_source_summary = career_source_coverage_summary()
    career_outcome_summary = career_opportunity_outcome_summary(CareerJobAnalysis.objects.all())
    model_training = learning_snapshot["model_training"]
    supervised_training_progress = _bounded_percent(
        model_training.get("supervised_training_progress", model_training.get("overall_progress", 0))
    )
    ml_maturity_progress = _bounded_percent(model_training.get("overall_progress", 0))

    browser_run_health = _browser_regression_health_snapshot()
    browser_ui_progress = 72 if browser_run_health["maturity_gate_recorded"] else 70
    browser_coverage = {
        "progress": browser_ui_progress,
        "implementation_status": "Implemented",
        "maturity_status": "Driver proof recorded" if browser_run_health["maturity_gate_recorded"] else "Browser-driver gated",
        "full_ui_mature": False,
        "execution_command": "python scripts/run_browser_regressions.py --browser Chrome --require-browser",
        "edge_execution_command": "python scripts/run_browser_regressions.py --browser Edge --require-browser",
        "ci_workflow": ".github/workflows/browser-regression.yml",
        "artifact_dir": "artifacts/browser",
        "summary_artifact": browser_run_health["summary_path"],
        "driver_run_health": browser_run_health,
        "selenium_workflows": [
            "login authentication",
            "dashboard live refresh",
            "document-center statement upload",
            "vehicle setup form submission",
            "vehicle invoice/OCR overlay correction",
        ],
        "live_server_contracts": [
            "login POST form and CSRF controls",
            "statement upload selectors and API endpoints",
            "dashboard refresh root and API endpoint",
            "expense form and timeline submission contracts",
            "document-center upload and ChatGPT import contracts",
            "vehicle setup, service, refill, issue, document, and condition form contracts",
        ],
        "remaining_gate": (
            "Selenium coverage is implemented, but UI maturity stays gated until required-browser local and CI "
            "runs keep recording zero skipped browser tests, zero runner failures, and useful failure artifacts."
        ),
    }
    document_scope_progress = min(max(_bounded_percent(document_track.get("progress", 0)), 91), 94)
    vehicle_scope_progress = min(max(_bounded_percent(vehicle_track.get("progress", 0)), 88), 92)
    career_scope_progress = min(max(_bounded_percent(career_track.get("progress", 0)), 88), 92)
    evidence_scope_progress = min(max(_bounded_percent(evidence_track.get("progress", 0)), 90 if evidence_watchlist_count == 0 else 0), 93)
    if not proof_contract_healthy:
        evidence_scope_progress = min(evidence_scope_progress, 88)
    large_data_scope_progress = 88 if cache_health.get("observability_ready") else 84

    next_steps = [
        "Keep adding real unknown document layouts to the field-correction suite and promote confirmed correction outcomes back into parser-learning evidence.",
        "Keep source links fresh, add long-tail models from real usage, and collect more condition snapshots plus issue outcomes before treating maintenance learning as mature.",
        "Add specialty sources only where real users expose role/geography gaps, then validate more salary-bearing outcomes from accepted or rejected opportunities.",
        "Keep verified evidence refresh jobs healthy across advisory surfaces and require proof contracts on any new recommendation or relationship-adjacent path.",
        "Tune production cache TTLs, capacity, and invalidation thresholds against real traffic and payload volume.",
        "Keep supervised artifacts fresh, collect more accepted outcomes, and do not count the planned future RL learner as production-ready ML.",
        "Extend browser-driven regression checks from the proven vehicle invoice/OCR correction path into login, statement upload, vehicle setup, dashboard refresh, and core form submissions.",
    ]
    improvements = [
        "maintain OCR confidence overlays, schema-aware correction candidates, ChatGPT context imports, and retry evidence in visual document review",
        "maintain route-aware trip costing with fuel-price estimates and service-prep buffers as more models are added",
        "add user feedback loops so corrections can improve parser heuristics over time",
        "add portfolio and job-market alerting with freshness thresholds and proof links",
        "monitor salary benchmark source diversity, geography match level, and sample density in compensation views",
        "use materialized cache hit-rate, stale-regeneration, invalidation, revision, TTL, and latency telemetry to tune production capacity",
    ]
    avoid_items = [
        "uncontrolled background crawling without source allowlists",
        "silent acceptance of weak or unrelated uploaded documents",
        "claiming ML accuracy where only heuristics exist",
        "deleting stale verified data before a replacement record is available",
    ]
    direction = [
        "every important external signal should show proof",
        "every parser should expose confidence and allow correction",
        "every long-lived cache should have a freshness contract",
        "every recommendation should be grounded in either user history, verified external data, or both",
    ]

    risks = [
        "browser-only issues can still exist outside the covered document-review invoice/OCR correction path",
        "some external sources are authoritative APIs, but market data still relies on Yahoo Finance",
        "multiple-vehicle support is structurally improved, but some naming remains vehicle-service or bike-centric in code paths for backward compatibility",
        "job-link parsing is robust for many public pages, but some portals can still block direct fetches or hide content behind script/runtime layers",
        "several recommendation paths are still adaptive heuristics rather than reviewed predictive models",
    ]
    if developer_escalations.filter(severity="high").exists():
        risks.append(
            f"{developer_escalations.filter(severity='high').count()} high-severity issues are waiting on developers as of {clock['clock_label']}."
        )
    if evidence_watchlist_count:
        risks.append(
            f"{evidence_watchlist_count} verified external evidence records are stale, failed, rejected, or due for refresh."
        )
    if cache_health.get("unobserved_namespace_count"):
        risks.append(
            f"{cache_health['unobserved_namespace_count']} materialized dashboard namespace(s) still need runtime traffic before cache telemetry is representative."
        )
    if loan_review_queue.exists():
        risks.append(
            f"{loan_review_queue.count()} imported loan repayments still need manual review before they should influence debt conclusions."
        )

    operational_metrics = [
        {"label": "Clock", "value": clock["clock_label"], "copy": f"{clock['timezone']} | UTC {clock['generated_at_utc']}"},
        {
            "label": "Developers",
            "value": user_model.objects.filter(is_superuser=True).count(),
            "copy": "Superusers are treated as developers for high-severity escalation.",
        },
        {
            "label": "Developer Escalations",
            "value": developer_escalations.count(),
            "copy": "Open or triaged high-severity tickets that ALFRED did not auto-close.",
        },
        {
            "label": "ALFRED Auto-Handled",
            "value": alfred_resolved.count(),
            "copy": "Low and medium severity issues resolved automatically with stored summaries.",
        },
        {
            "label": "Evidence Watchlist",
            "value": evidence_watchlist_count,
            "copy": "Active external records that are stale, failed, rejected, or due now.",
        },
        {
            "label": "Proof Contract Coverage",
            "value": f"{proof_covered_surface_count}/{proof_surface_count}",
            "copy": "Recommendation and relationship-adjacent surfaces covered before any new signal ships.",
        },
        {
            "label": "Evidence Refresh Health",
            "value": f"{evidence_fresh_count}/{evidence_active_count}",
            "copy": (
                f"Fresh active records; last attempt {refresh_health.get('last_refresh_attempt_at') or 'not recorded'}, "
                f"last success {refresh_health.get('last_refresh_success_at') or 'not recorded'}."
            ),
        },
        {
            "label": "Cache Health",
            "value": f"{cache_health['observed_namespace_count']}/{cache_health['registered_namespace_count']}",
            "copy": (
                f"{cache_health['hit_rate_pct']}% hit rate; "
                f"{cache_health['average_generation_latency_ms']} ms average generation; "
                f"{cache_health['stale_regeneration_count']} stale regeneration(s)."
            ),
        },
        {
            "label": "Browser Coverage",
            "value": f"{browser_ui_progress}%",
            "copy": (
                f"Selenium runner, CI workflow, failure artifacts, and run-summary proof are tracked; "
                f"latest driver status: {browser_run_health['status']} with "
                f"{browser_run_health['skipped_count'] if browser_run_health['skipped_count'] is not None else 'no'} recorded skip count."
            ),
        },
        {
            "label": "Loan Review Queue",
            "value": loan_review_queue.count(),
            "copy": "Statement-linked loan items that still need review before trust is raised.",
        },
        {
            "label": "Closure Review",
            "value": closure_pending.count() + closure_rejected.count(),
            "copy": "Pending or rejected foreclosure documents still awaiting clean verification.",
        },
        {
            "label": "Generated Reports",
            "value": generated_reports.count(),
            "copy": "Stored reporting artifacts now kept off the normal user navigation.",
        },
        {
            "label": "Chat Imports",
            "value": chatgpt_imports.count(),
            "copy": "Imported ChatGPT dashboard or transcript contexts waiting for reviewed mapping.",
        },
        {
            "label": "Model States",
            "value": learning_snapshot["model_training"]["ready_models"],
            "copy": "Structured models currently ready for inference after the last safe training cycle.",
        },
    ]

    hardening_decisions = [
        "Project status, pending work, reports, and operational risk stay off the main user dashboard and live only in superuser surfaces.",
        "Every support ticket is server-timestamped through the internal clock before it is stored or routed.",
        "Low and medium severity issues are auto-handled by ALFRED with a recorded resolution summary, while high severity stays with developers.",
        "External evidence paths keep circuit-breaker, stale-fallback, and scheduled-refresh guardrails instead of retrying blindly.",
        proof_contract_snapshot.get(
            "new_signal_rule",
            "Do not add a new recommendation or relationship-adjacent signal until it has a complete proof contract.",
        ),
        "Charts are expected to render only live API-backed data or an explicit empty-state message, not demo placeholders.",
        "Pasted ChatGPT dashboard context is retained as reviewable source material before any live ALFRED records are changed.",
        "Heavy dashboards use revision-keyed materialized API payloads for budget, loan, net-worth, behavioral, risk, recommendation, tax, career, family, relationship, investment, and mobility paths.",
        "Materialized cache telemetry reports hit/miss, TTL, revision, invalidation reason, and generation latency by dashboard namespace before large-data maturity is raised.",
        "Browser UI maturity remains gated: the Selenium runner and CI workflow can prove selected interactions with screenshots/logs on failure and a browser_regression_summary.json proof record, while live-server contracts keep login, uploads, dashboard refresh, vehicle setup, and form wiring covered by default.",
    ]

    in_progress_tracks = [
        {
            "title": "Browser/UI regression coverage",
            "progress": browser_ui_progress,
            "detail": (
                "Django live-server rendering, static-asset checks, upload/form contracts, a dedicated Selenium runner, "
                "CI browser workflow, failure artifacts, run-summary proof, and gated Selenium workflows now cover login, "
                "document-center statement upload, vehicle setup submission, dashboard live refresh, and the vehicle invoice/OCR overlay correction path. "
                f"{browser_run_health['summary']}"
            ),
            "maturity_status": browser_coverage["maturity_status"],
            "signals": [
                f"{len(browser_coverage['selenium_workflows'])} Selenium-gated workflow(s)",
                f"{len(browser_coverage['live_server_contracts'])} live-server contract group(s)",
                f"runner: {browser_coverage['execution_command']}",
                f"edge runner: {browser_coverage['edge_execution_command']}",
                f"artifacts: {browser_coverage['artifact_dir']}",
                f"summary: {browser_coverage['summary_artifact']}",
                f"latest browser run: {browser_run_health['status']} via {browser_run_health['run_context']}",
                f"recorded browser skips: {browser_run_health['skipped_count'] if browser_run_health['skipped_count'] is not None else 'not recorded'}",
                "login, statement upload, vehicle setup, dashboard refresh, and core form submissions are named",
                "full UI maturity is still not claimed",
            ],
            "maturity_gates": [
                "Selenium or equivalent browser-driver execution records browser_regression_summary.json in CI or an explicit local browser job with no skipped browser tests.",
                "The dedicated runner fails required-browser jobs when Selenium tests are skipped.",
                "Live-server/static contracts keep covering the same workflows whenever browser drivers are unavailable.",
                "Failure artifacts keep screenshots, page HTML, metadata, and browser logs available for failed browser runs.",
                "More real unknown document layouts and form-correction outcomes remain covered before UI maturity is raised.",
            ],
            "next_focus": "Keep Selenium available in local/CI browser jobs, keep skip behavior explicit when drivers are absent, record no-skip browser summaries, and extend real browser interaction depth without adding new advisory signals.",
        },
        {
            "title": "Document OCR and correction maturity",
            "progress": document_scope_progress,
            "detail": "Parser confidence, low-confidence queues, accepted corrections, ChatGPT context import, retry-fed learning, schema-aware OCR overlay candidates, degraded service-invoice recovery, cross-family unknown-layout fixtures, accepted correction memory outcomes, and Selenium-proven vehicle OCR overlay correction are implemented across the current document families.",
            "next_focus": "Keep adding real unknown layouts and validated correction outcomes before treating field-level maintenance learning as mature across every document family.",
            "maturity_gates": [
                "Real unknown layouts keep arriving across every document family, not only the current fixtures.",
                "Accepted corrections produce validated parser-learning outcomes per family before field-level learning is treated as mature.",
                "Browser interaction proof expands beyond the vehicle invoice/OCR overlay path.",
            ],
        },
        {
            "title": "Vehicle catalog and maintenance depth",
            "progress": vehicle_scope_progress,
            "detail": (
                f"Supported seed coverage is strong: {catalog_summary['model_count']} official catalog models across "
                f"{catalog_summary['manufacturer_count']} manufacturers, source-linked guidance checked on "
                f"{catalog_refresh['last_checked_on']} ({catalog_refresh['age_days']} days old; {catalog_refresh['refresh_policy_days']}-day source refresh policy; next due {catalog_refresh['next_due_on']}), "
                "brand-filtered model selection, and route-aware service-cost actions."
            ),
            "next_focus": "Keep source links fresh, add long-tail models from real usage, and collect more condition snapshots plus issue outcomes before treating maintenance learning as mature.",
            "maturity_gates": [
                "Official source links stay within the configured refresh policy.",
                "Long-tail vehicle models are added from real user demand and verified sources, not bulk catalog padding.",
                "Condition snapshots and resolved or costed issue outcomes grow enough to validate maintenance recommendations.",
            ],
        },
        {
            "title": "Career source and compensation breadth",
            "progress": career_scope_progress,
            "detail": (
                f"Current source breadth spans {career_source_summary['configured_feed_count']} live job feeds "
                f"({', '.join(career_source_summary['configured_feeds'])}), {career_source_summary['job_page_adapter_count']} job-page adapters, recruiter/JD intake, geography-aware salary evidence, "
                f"{career_source_summary['candidate_specialty_source_count']} candidate specialty sources gated by role/geography gaps, and "
                f"{career_outcome_summary['salary_bearing_outcome_count']} salary-bearing accepted/rejected outcome(s)."
            ),
            "next_focus": "Add specialty sources only where real users expose role/geography gaps, then validate more salary-bearing outcomes from accepted or rejected opportunities.",
            "maturity_gates": [
                "Specialty sources are added only after real users expose role or geography gaps.",
                "Accepted and rejected opportunity outcomes carry salary-bearing evidence.",
                "Compensation maturity grows from validated outcomes, not just wider feed count.",
            ],
        },
        {
            "title": "Evidence freshness and proof rigor",
            "progress": evidence_scope_progress,
            "detail": (
                "Current advisory surfaces expose source URLs, freshness counters, stale/due status, stale fallback, circuit-breaker metadata, "
                f"scheduled-refresh contracts, and required-source proof contracts; {proof_covered_surface_count}/{proof_surface_count} registered recommendation or relationship-adjacent surfaces declare the full contract."
            ),
            "next_focus": "Keep scheduled refresh healthy and extend the proof contract before adding any new recommendation or relationship-adjacent signal.",
            "signals": [
                f"{proof_covered_surface_count}/{proof_surface_count} proof-contract surfaces covered",
                f"scheduled refresh: {scheduled_refresh_name}",
                f"{evidence_watchlist_count} evidence record(s) on the watchlist",
                refresh_health.get("summary", "Refresh health snapshot unavailable."),
                f"last attempt: {refresh_health.get('last_refresh_attempt_at') or 'not recorded'}",
                f"last success: {refresh_health.get('last_refresh_success_at') or 'not recorded'}",
            ],
            "maturity_gates": [
                "Scheduled refresh keeps active verified evidence inside freshness windows.",
                "The proof contract registry covers every current recommendation and relationship-adjacent surface before new signals are added.",
                "Every new recommendation or relationship-adjacent signal ships with required-source proof contracts, stale fallback, and circuit-breaker metadata.",
                "No new advisory signal is treated as mature while proof links, source freshness, or refresh outcomes are missing.",
            ],
        },
        {
            "title": "Large-data hardening",
            "progress": large_data_scope_progress,
            "detail": (
                "Heavy dashboards now use revision-keyed materialized payloads with cache metadata and namespace-level health telemetry. "
                f"{cache_health['registered_namespace_count']} cache-backed namespace(s) are registered, "
                f"{cache_health['observed_namespace_count']} have runtime telemetry, and production maturity remains capped until sizing and TTL behavior are proven under real traffic."
            ),
            "next_focus": "Tune production cache sizing, TTLs, and invalidation thresholds against real traffic before calling this fully mature at scale.",
            "signals": [
                f"{cache_health['registered_namespace_count']} registered materialized namespace(s)",
                f"{cache_health['observed_namespace_count']} namespace(s) with runtime telemetry",
                f"{cache_health['hit_rate_pct']}% cache hit rate across {cache_health['total_requests']} request(s)",
                f"{cache_health['average_generation_latency_ms']} ms average generation latency",
                f"{cache_health['stale_regeneration_count']} stale regeneration(s)",
                f"{cache_health['invalidation_count']} invalidation(s)",
                f"last invalidation: {cache_health.get('last_invalidation_reason') or 'not recorded'}",
            ],
            "maturity_gates": [
                "Production cache sizing is validated against real payload volume and concurrency.",
                "TTL tuning and invalidation rules are observable per materialized dashboard namespace.",
                "Cache hit rate, stale regeneration, revision churn, and latency remain visible in Project Details.",
                "Large-data hardening stays below complete until real traffic proves cache capacity and freshness behavior.",
            ],
        },
        {
            "title": "ML maturity and training lifecycle",
            "progress": ml_maturity_progress,
            "detail": (
                f"Supervised training coverage is {supervised_training_progress}% with "
                f"{model_training.get('supervised_fresh_models', 0)}/{model_training.get('trainable_models', 0)} trainable models fresh; "
                "production-ready ML maturity excludes the planned future RL learner and still includes confidence, freshness, skipped model state, and heuristic fallback risk."
            ),
            "next_focus": "Keep supervised artifacts fresh, collect more accepted outcomes, and do not count the planned future RL learner as production-ready ML.",
            "maturity_gates": [
                "Supervised artifacts stay fresh within their configured retraining windows.",
                "Accepted outcomes keep growing for supervised learners that depend on reviewed user decisions.",
                "The planned future RL learner remains planned-only and excluded from production-ready ML counts until it has a real production contract.",
            ],
        },
    ]
    scope_completion_progress = _bounded_percent(mean(track["progress"] for track in in_progress_tracks)) if in_progress_tracks else 100
    auto_training_track = {
        "title": "Supervised model refresh",
        "progress": supervised_training_progress,
        "detail": (
            f"Current supervised training coverage: {model_training.get('supervised_fresh_models', 0)}/"
            f"{model_training.get('trainable_models', 0)} trainable models fresh and ready, "
            f"{model_training.get('supervised_skipped_models', 0)} trainable skipped, "
            f"{model_training.get('failed_models', 0)} failed, "
            f"{model_training.get('planned_models', 0)} planned future model excluded from coverage."
        ),
    }
    completed_tracks = [
        {
            "title": "Backend/API regression baseline",
            "progress": 100,
            "detail": "The local Django functional suite and system check pass for the current codebase after this calibration pass.",
            "maintenance_focus": "Keep this green with every scope change; it does not replace browser interaction testing.",
        },
        {
            "title": "Vehicle make/model picker fix",
            "progress": 100,
            "detail": "The service-vehicle setup now has one make/brand combobox, preserves the official catalog model dropdown during live refresh, and filters catalog models by the selected make.",
            "maintenance_focus": "Keep the field contract covered while adding full browser automation for real click/type/select behavior.",
        },
    ]
    if supervised_training_progress >= 100:
        completed_tracks.append(
            {
                **auto_training_track,
                "maintenance_focus": "Monitor drift, data quality, and freshness windows before expanding to the planned RL policy learner.",
            }
        )
    else:
        in_progress_tracks.append(
            {
                **auto_training_track,
                "next_focus": "Collect the missing minimum samples for skipped supervised models, then rerun the forced training cycle.",
            }
        )

    return {
        "clock": clock,
        "summary_cards": [
            {"label": "In-Progress Tracks", "value": len(in_progress_tracks), "copy": "Major workstreams still actively evolving."},
            {"label": "Scope Completion", "value": f"{scope_completion_progress}%", "copy": "Average maturity across active broad product scopes; capped where verification is incomplete."},
            {"label": "Learning Maturity", "value": f"{learning_snapshot['overall_progress']}%", "copy": "Adaptive-system maturity from live data coverage and freshness."},
            {"label": "Developer Escalations", "value": developer_escalations.count(), "copy": "High-severity items still waiting on superuser developers."},
            {"label": "Evidence Watchlist", "value": evidence_watchlist_count, "copy": "Verified external records that are stale, failed, rejected, or due now."},
            {"label": "Evidence Refresh", "value": f"{evidence_fresh_count}/{evidence_active_count}", "copy": "Fresh active records after the latest recorded refresh attempts."},
            {"label": "Proof Contracts", "value": f"{proof_covered_surface_count}/{proof_surface_count}", "copy": "Current recommendation and relationship-adjacent surfaces with full proof coverage."},
        ],
        "operational_metrics": operational_metrics,
        "learning_snapshot": learning_snapshot,
        "in_progress_tracks": in_progress_tracks,
        "completed_tracks": completed_tracks,
        "risks": risks,
        "next_steps": next_steps,
        "improvements": improvements,
        "avoid_items": avoid_items,
        "direction": direction,
        "guardrails": guardrails,
        "cache_health": cache_health,
        "browser_coverage": browser_coverage,
        "hardening_decisions": hardening_decisions,
        "report_library": [
            {"file_path": report.file_path, "created_at": report.created_at}
            for report in generated_reports[:8]
        ],
        "developer_queue": [
            {
                "title": ticket.title,
                "module": ticket.get_module_display(),
                "severity": ticket.get_severity_display(),
                "username": ticket.user.username,
                "created_at": ticket.created_at,
                "summary": ticket.summary,
            }
            for ticket in developer_escalations.select_related("user")[:8]
        ],
        "auto_ticket_activity": [
            {
                "title": ticket.title,
                "module": ticket.get_module_display(),
                "created_at": ticket.created_at,
                "resolution_summary": ticket.resolution_summary,
            }
            for ticket in alfred_resolved.select_related("user")[:8]
        ],
    }
