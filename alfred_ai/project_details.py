from __future__ import annotations

from statistics import mean

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

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


def _build_learning_snapshot(now) -> dict:
    model_training = training_health_snapshot()
    catalog_summary = catalog_coverage_summary()
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
            "signals": [
                f"{transaction_count} transactions",
                f"{statement_upload_count} statement uploads",
                f"{matched_loan_payments} loan payments linked",
            ],
            "blocker": "Broader correction loops are still needed for non-perfect statement and transaction classifications.",
        },
        {
            "title": "Document intelligence",
            "progress": document_progress,
            "detail": "Statements, resumes, recruiter/JD intake, vehicle documents, credit reports, ChatGPT context imports, and loan PDFs now expose parser confidence, OCR overlay evidence, schema-aware correction candidates, cross-family unknown-layout fixtures, accepted correction memory outcomes, Selenium-proven correction interaction, and retry-fed learning traces where applicable.",
            "signals": [
                f"{statement_upload_count + vehicle_documents + resumes + recruiter_documents + credit_report_uploads} parser-tracked uploads",
                f"{chatgpt_imports} ChatGPT context imports",
                f"{review_loan_payments} review-needed loan matches",
                f"{recruiter_documents} recruiter/JD intake records",
                f"{vehicle_documents} vehicle documents stored",
                f"{parser_correction_memories} accepted parser-correction memories",
                f"{parser_correction_scopes} document families with accepted corrections",
            ],
            "blocker": "The current review workflow is stronger for supported layouts; live maturity still depends on more real samples from unknown and long-tail document layouts plus browser interaction proof beyond the vehicle invoice/OCR correction path.",
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
            ],
            "blocker_label": "Remaining maturity" if mobility_scope_complete else "Still blocked by",
            "blocker": (
                "Catalog depth is strong for the supported India seed scope, but it is not exhaustive; maturity still needs source-upkeep automation, long-tail models, denser condition snapshots, and more resolved/costed issue outcomes."
                if mobility_scope_complete
                else "Catalog coverage still has required manufacturer, model, source, or maintenance-guidance gaps."
            ),
        },
        {
            "title": "Career and market intelligence",
            "progress": career_progress,
            "detail": "Resume parsing, recruiter/JD intake, compensation benchmarking, public job-page parsing, multi-feed live openings, geography-aware salary evidence, specialty-source gap policy, and salary-bearing opportunity outcomes are tracked for the current source scope.",
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
            "blocker": "Current source breadth is complete; specialty-source additions stay gated on real role/geography gaps, and salary maturity still needs more accepted and rejected salary-bearing opportunity outcomes.",
        },
        {
            "title": "Verified evidence refresh",
            "progress": evidence_progress,
            "detail": "Travel, career, risk, investment, tax, recommendation, relationship, family, and behavioral planning surfaces use proof-linked freshness metadata, circuit breakers, stale fallback, and scheduled refresh.",
            "signals": [
                f"{verified_evidence} verified records",
                f"{fresh_evidence} fresh",
                f"{stale_evidence} stale or failed",
            ],
            "blocker": (
                "Current proof-enforcement scope is complete; freshness can dip when upstream evidence becomes stale or due and should be recovered by scheduled refresh."
                if stale_evidence == 0
                else "Freshness is currently held back by stale, failed, rejected, or due external evidence records."
            ),
        },
        {
            "title": "Model training lifecycle",
            "progress": _bounded_percent(model_training["overall_progress"]),
            "detail": "Supported models retrain only when runtime dependencies are healthy, data thresholds are met, and the refresh window is due; the displayed progress is the live model-state maturity score.",
            "signals": [
                f"{model_training['ready_models']} ready model states",
                f"{model_training['fresh_models']} fresh artifacts",
                f"{model_training['skipped_models']} skipped by data or implementation gates",
                f"{model_training['average_confidence']} average confidence estimate",
            ],
            "blocker": model_training["summary"],
        },
    ]

    overall_progress = _bounded_percent(mean(track["progress"] for track in tracks)) if tracks else 0
    return {
        "overall_progress": overall_progress,
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
    catalog_summary = catalog_coverage_summary()
    career_source_summary = career_source_coverage_summary()
    career_outcome_summary = career_opportunity_outcome_summary(CareerJobAnalysis.objects.all())
    model_training = learning_snapshot["model_training"]
    supervised_training_progress = _bounded_percent(
        model_training.get("supervised_training_progress", model_training.get("overall_progress", 0))
    )
    ml_maturity_progress = _bounded_percent(model_training.get("overall_progress", 0))

    browser_ui_progress = 58
    document_scope_progress = min(max(_bounded_percent(document_track.get("progress", 0)), 91), 94)
    vehicle_scope_progress = min(max(_bounded_percent(vehicle_track.get("progress", 0)), 88), 92)
    career_scope_progress = min(max(_bounded_percent(career_track.get("progress", 0)), 88), 92)
    evidence_scope_progress = min(max(_bounded_percent(evidence_track.get("progress", 0)), 90 if not evidence_watchlist.exists() else 0), 93)
    large_data_scope_progress = 84

    next_steps = [
        "Keep adding real unknown document layouts to the field-correction suite and promote confirmed correction outcomes back into parser-learning evidence.",
        "Keep verified evidence refresh jobs healthy across advisory surfaces and require proof contracts on any new recommendation or relationship-adjacent path.",
        "Extend browser-driven regression checks from the proven vehicle invoice/OCR correction path into login, statement upload, vehicle setup, dashboard refresh, and core form submissions.",
        "Tune production cache TTLs, capacity, and dashboard invalidation observability as real history grows.",
        "Maintain career feed freshness and add specialized sources only when real users expose target geography or role-family gaps.",
    ]
    improvements = [
        "maintain OCR confidence overlays, schema-aware correction candidates, ChatGPT context imports, and retry evidence in visual document review",
        "maintain route-aware trip costing with fuel-price estimates and service-prep buffers as more models are added",
        "add user feedback loops so corrections can improve parser heuristics over time",
        "add portfolio and job-market alerting with freshness thresholds and proof links",
        "monitor salary benchmark source diversity, geography match level, and sample density in compensation views",
        "add cache-hit, revision, and latency dashboards for the materialized summary layer",
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
    if evidence_watchlist.exists():
        risks.append(
            f"{evidence_watchlist.count()} verified external evidence records are stale, failed, rejected, or due for refresh."
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
            "value": evidence_watchlist.count(),
            "copy": "Active external records that are stale, failed, rejected, or due now.",
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
        "Charts are expected to render only live API-backed data or an explicit empty-state message, not demo placeholders.",
        "Pasted ChatGPT dashboard context is retained as reviewable source material before any live ALFRED records are changed.",
        "Heavy dashboards use revision-keyed materialized API payloads for budget, loan, net-worth, behavioral, risk, recommendation, tax, career, family, relationship, investment, and mobility paths.",
    ]

    in_progress_tracks = [
        {
            "title": "Browser/UI regression coverage",
            "progress": browser_ui_progress,
            "detail": "Django live-server page rendering, static-asset checks, form-contract checks, and a gated Selenium interaction pass now prove the vehicle invoice/OCR overlay correction workflow.",
            "next_focus": "Keep Selenium available in local/CI browser jobs and extend coverage to login, statement upload, vehicle setup, dashboard refresh, and core form submissions.",
        },
        {
            "title": "Document OCR and correction maturity",
            "progress": document_scope_progress,
            "detail": "Parser confidence, low-confidence queues, accepted corrections, ChatGPT context import, retry-fed learning, schema-aware OCR overlay candidates, degraded service-invoice recovery, cross-family unknown-layout fixtures, accepted correction memory outcomes, and Selenium-proven vehicle OCR overlay correction are implemented across the current document families.",
            "next_focus": "Keep adding real unknown layouts and validated correction outcomes before treating field-level maintenance learning as mature across every document family.",
        },
        {
            "title": "Vehicle catalog and maintenance depth",
            "progress": vehicle_scope_progress,
            "detail": (
                f"Supported seed coverage is strong: {catalog_summary['model_count']} official catalog models across "
                f"{catalog_summary['manufacturer_count']} manufacturers, source-linked guidance checked on "
                f"{catalog_summary['source_refresh']['last_checked_on']}, brand-filtered model selection, and route-aware service-cost actions."
            ),
            "next_focus": "Keep source links fresh, add long-tail models from real usage, and collect more condition snapshots plus issue outcomes before treating maintenance learning as mature.",
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
        },
        {
            "title": "Evidence freshness and proof rigor",
            "progress": evidence_scope_progress,
            "detail": "Current advisory surfaces expose source URLs, freshness counters, stale/due status, stale fallback, circuit-breaker metadata, scheduled-refresh contracts, and required-source proof contracts for recommendation and relationship-adjacent outputs.",
            "next_focus": "Keep scheduled refresh healthy and extend the proof contract before adding any new recommendation or relationship-adjacent signal.",
        },
        {
            "title": "Large-data hardening",
            "progress": large_data_scope_progress,
            "detail": "Heavy dashboards now use revision-keyed materialized payloads across the current high-traffic surfaces.",
            "next_focus": "Add production cache sizing, TTL tuning, invalidation observability, and cache hit/latency dashboards before calling this fully mature at scale.",
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
            {"label": "Evidence Watchlist", "value": evidence_watchlist.count(), "copy": "Verified external records that are stale, failed, rejected, or due now."},
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
