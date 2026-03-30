from __future__ import annotations

from statistics import mean

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.career.models import CareerJobAnalysis, CareerResume
from apps.expenses.models import Expense, StatementUpload
from apps.integrations.models import VerifiedExternalInsight
from apps.loans.models import LoanClosureDocument, LoanPaymentHistory
from apps.mobility.models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeServiceRecord
from apps.reports.models import GeneratedReport, SystemTicket
from .internal_clock import clock_snapshot


def _progress(current: float, target: float, *, floor: int = 10, ceiling: int = 95) -> int:
    if target <= 0:
        return floor
    ratio = max(0.0, min(current / target, 1.0))
    return max(floor, min(ceiling, round(floor + ((ceiling - floor) * ratio))))


def _build_learning_snapshot(now) -> dict:
    transaction_count = Expense.objects.count()
    statement_upload_count = StatementUpload.objects.count()
    matched_loan_payments = LoanPaymentHistory.objects.filter(match_status="matched").count()
    review_loan_payments = LoanPaymentHistory.objects.filter(match_status="review").count()

    vehicle_documents = BikeDocument.objects.count()
    service_records = BikeServiceRecord.objects.count()
    condition_snapshots = BikeConditionSnapshot.objects.count()
    vehicle_issues = BikeIssueReport.objects.count()

    resumes = CareerResume.objects.count()
    job_analyses = CareerJobAnalysis.objects.count()

    verified_evidence = VerifiedExternalInsight.objects.filter(is_active=True).count()
    fresh_evidence = VerifiedExternalInsight.objects.filter(is_active=True).filter(
        Q(status="verified") & (Q(stale_after__isnull=True) | Q(stale_after__gt=now))
    ).count()
    stale_evidence = VerifiedExternalInsight.objects.filter(is_active=True).filter(
        Q(status__in=["stale", "failed", "rejected"]) | Q(stale_after__lte=now)
    ).count()

    finance_progress = _progress(transaction_count + (statement_upload_count * 12) + (matched_loan_payments * 8), 420, floor=18)
    document_progress = max(
        14,
        _progress(vehicle_documents + statement_upload_count + resumes, 42, floor=20) - min(review_loan_payments * 2, 10),
    )
    mobility_progress = _progress(service_records + condition_snapshots + vehicle_issues + (vehicle_documents * 0.5), 54, floor=16)
    career_progress = _progress((resumes * 14) + (job_analyses * 18) + (fresh_evidence * 2), 140, floor=15)
    evidence_progress = max(12, _progress(fresh_evidence, max(verified_evidence, 1), floor=22) - min(stale_evidence * 3, 25))

    tracks = [
        {
            "title": "Finance behavior learning",
            "progress": finance_progress,
            "detail": "Expense classification, emotional-spend scoring, anomaly detection, and statement-linked loan recognition are learning from live transaction history.",
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
            "detail": "Statements, resumes, vehicle documents, and loan PDFs now expose parser confidence, but correction queues and OCR review are still pending.",
            "signals": [
                f"{statement_upload_count + vehicle_documents + resumes} parser-tracked uploads",
                f"{review_loan_payments} review-needed loan matches",
                f"{vehicle_documents} vehicle documents stored",
            ],
            "blocker": "Unknown layouts still need a user-facing correction and feedback workflow.",
        },
        {
            "title": "Vehicle maintenance learning",
            "progress": mobility_progress,
            "detail": "Service bills, condition snapshots, issue history, and parts-impact reasoning are now blended into the vehicle dashboard.",
            "signals": [
                f"{service_records} service logs",
                f"{condition_snapshots} condition snapshots",
                f"{vehicle_issues} issue reports",
            ],
            "blocker": "Model-specific maintenance schedules and richer route-aware wear/cost signals are still missing.",
        },
        {
            "title": "Career and market intelligence",
            "progress": career_progress,
            "detail": "Resume parsing, fit analysis, and market signals are active, but the pipeline is still partly heuristic and source coverage is not broad enough yet.",
            "signals": [
                f"{resumes} resumes",
                f"{job_analyses} job analyses",
                f"{fresh_evidence} fresh evidence records",
            ],
            "blocker": "Recruiter-mail parsing, salary benchmarks, and wider source coverage remain open.",
        },
        {
            "title": "Verified evidence refresh",
            "progress": evidence_progress,
            "detail": "External signals now use freshness windows, circuit breakers, stale fallback, and scheduled refresh rather than one-off fetches.",
            "signals": [
                f"{verified_evidence} verified records",
                f"{fresh_evidence} fresh",
                f"{stale_evidence} stale or failed",
            ],
            "blocker": "The same freshness and proof contracts still need to cover more recommendation and relationship paths.",
        },
    ]

    overall_progress = round(mean(track["progress"] for track in tracks)) if tracks else 0
    return {
        "overall_progress": overall_progress,
        "summary": "ALFRED is adaptive and AI-assisted across multiple modules, but the whole product is not yet fully model-trained end-to-end. Several important paths still blend ML components with rule-based and evidence-backed heuristics.",
        "tracks": sorted(tracks, key=lambda item: item["progress"]),
        "implementation_state": {
            "ml_backed": [
                "Behavioral anomaly detection, signature generation, and savings-strategy personalization run on stored transaction history.",
                "Expense enrichment applies model-style confidence scoring and emotional-spend detection to imported and manual entries.",
                "Parser confidence is stored for resumes, statements, vehicle documents, and loan PDFs.",
            ],
            "adaptive_blended": [
                "Career timing, risk radar, vehicle fault diagnosis, and travel readiness are adaptive but still blend verified evidence with heuristics.",
                "Vehicle dashboard suggestions adjust with service history, fault history, condition snapshots, and document state.",
                "Verified external intelligence refreshes in the background with freshness contracts, stale fallback, and circuit breakers.",
            ],
            "not_yet_fully_learned": [
                "Unknown document layouts do not yet improve through a user correction queue.",
                "Job-source coverage, salary benchmarks, and portfolio/recommendation signals are not yet broad enough to claim mature learning.",
                "Large-data aggregations are still request-time reads in many paths and are not yet moved to materialized/cache layers.",
            ],
        },
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

    learning_snapshot = _build_learning_snapshot(now)

    next_steps = [
        "Add parser correction and review queues so user fixes can improve future parsing instead of staying manual.",
        "Expand verified evidence beyond travel, career, and risk into recommendation, tax, and relationship signals where appropriate.",
        "Move large dashboard aggregations to cache or materialized layers if the current history size keeps growing.",
        "Broaden official vehicle catalog coverage and model-specific maintenance schedules across more bikes, scooters, and cars.",
        "Expand career intelligence to more job sources, recruiter-email parsing, and geography-aware salary evidence.",
    ]
    improvements = [
        "add OCR confidence overlays and visual document review",
        "support route-aware trip costing with fuel-price estimates and service-prep buffers",
        "add user feedback loops so corrections can improve parser heuristics over time",
        "add portfolio and job-market alerting with freshness thresholds and proof links",
        "add salary benchmark sources with evidence and geography-aware compensation views",
        "replace more request-time aggregations with cache-aware summary layers when data volume grows materially",
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
        "browser-only issues can still exist where no live frontend interaction pass was run",
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
    ]

    hardening_decisions = [
        "Project status, pending work, reports, and operational risk stay off the main user dashboard and live only in superuser surfaces.",
        "Every support ticket is server-timestamped through the internal clock before it is stored or routed.",
        "Low and medium severity issues are auto-handled by ALFRED with a recorded resolution summary, while high severity stays with developers.",
        "External evidence paths keep circuit-breaker, stale-fallback, and scheduled-refresh guardrails instead of retrying blindly.",
        "Charts are expected to render only live API-backed data or an explicit empty-state message, not demo placeholders.",
    ]

    in_progress_tracks = [
        {
            "title": "Document correction workflow",
            "progress": max(learning_snapshot["tracks"][1]["progress"], 24),
            "detail": "Parser confidence is already stored, but end-user correction queues and OCR review overlays are still being built.",
            "next_focus": "Expose review queues for low-confidence documents and use accepted corrections to improve future parsing.",
        },
        {
            "title": "Cross-module proof enforcement",
            "progress": max(learning_snapshot["tracks"][4]["progress"] - 12, 18),
            "detail": "Travel, career, and risk carry proof-linked evidence today, but recommendation, tax, and relationship paths still need the same contract.",
            "next_focus": "Expand verified evidence and freshness metadata into the remaining advisory modules.",
        },
        {
            "title": "Vehicle catalog and maintenance depth",
            "progress": max(learning_snapshot["tracks"][2]["progress"] - 8, 20),
            "detail": "Vehicle maintenance intelligence is live, but official catalog coverage and model-specific schedules are still incomplete.",
            "next_focus": "Broaden official manufacturer coverage and attach more model-specific maintenance guidance.",
        },
        {
            "title": "Career source coverage",
            "progress": max(learning_snapshot["tracks"][3]["progress"] - 10, 18),
            "detail": "Resume parsing and role-fit are active, but recruiter-mail parsing, salary benchmarks, and wider job-source coverage are still in flight.",
            "next_focus": "Add recruiter-mail ingestion, compensation benchmarks, and more robust job-source adapters.",
        },
        {
            "title": "Large-data hardening",
            "progress": 42,
            "detail": "Indexes and selective summaries exist, but several large dashboards still aggregate request-time data directly.",
            "next_focus": "Move the heaviest dashboard aggregations to cache-aware materialized layers as history grows.",
        },
    ]

    return {
        "clock": clock,
        "summary_cards": [
            {"label": "In-Progress Tracks", "value": len(in_progress_tracks), "copy": "Major workstreams still actively evolving."},
            {"label": "Learning Progress", "value": f"{learning_snapshot['overall_progress']}%", "copy": "Overall adaptive-system maturity from live data coverage and freshness."},
            {"label": "Developer Escalations", "value": developer_escalations.count(), "copy": "High-severity items still waiting on superuser developers."},
            {"label": "Evidence Watchlist", "value": evidence_watchlist.count(), "copy": "Verified external records that are stale, failed, rejected, or due now."},
        ],
        "operational_metrics": operational_metrics,
        "learning_snapshot": learning_snapshot,
        "in_progress_tracks": in_progress_tracks,
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
