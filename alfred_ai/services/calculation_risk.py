from __future__ import annotations

from statistics import mean

from django.db.models import Q
from django.utils import timezone

from apps.career.models import CareerJobAnalysis, CareerResume
from apps.career.services.job_intelligence import career_opportunity_outcome_summary
from apps.expenses.models import Expense, StatementUpload
from apps.integrations.models import CreditReportUpload, VerifiedExternalInsight
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument, LoanPaymentHistory
from apps.ml_engine.models import AdaptiveModelState
from apps.mobility.models import BikeDocument, BikeIssueReport, BikeProfile


PARSER_REVIEW_STATUSES = ("pending", "needs_review", "failed")
EXTERNAL_CALCULATION_SCOPES = ("jobs", "news", "market", "macro", "tax", "career", "investment")


def _bounded_percent(value: float, *, default: int = 0) -> int:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(100, int(round(numeric))))


def _queue(label: str, key: str, count: int, *, scope: str = "global") -> dict:
    return {
        "key": key,
        "label": label,
        "count": int(count),
        "scope": scope,
        "state": "pending_review" if count else "clear",
    }


def _entry(
    *,
    key: str,
    label: str,
    status: str,
    progress: int,
    code_path: str,
    evidence: list[str] | None = None,
    blockers: list[str] | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "status": status,
        "progress": _bounded_percent(progress),
        "code_path": code_path,
        "evidence": evidence or [],
        "blockers": blockers or [],
    }


def calculation_risk_snapshot(*, guardrails: dict | None = None) -> dict:
    """Audit calculation-critical paths without changing product behavior."""

    now = timezone.now()
    guardrails = dict(guardrails or {})
    refresh_health = dict(guardrails.get("refresh_health") or {})

    transaction_count = Expense.objects.count()
    statement_review_count = StatementUpload.objects.filter(parser_status__in=PARSER_REVIEW_STATUSES).count()
    unreviewed_statement_transactions = Expense.objects.filter(
        statement_upload__parser_status__in=PARSER_REVIEW_STATUSES
    ).count()
    imported_transaction_count = Expense.objects.exclude(statement_upload__isnull=True).count()

    loans = Loan.objects.all()
    loan_count = loans.count()
    loan_repayment_review_count = LoanPaymentHistory.objects.filter(match_status="review").count()
    matched_loan_repayment_count = LoanPaymentHistory.objects.filter(match_status="matched").count()
    loan_import_review_count = LoanImportDocument.objects.filter(parser_status__in=PARSER_REVIEW_STATUSES).count()
    loan_closure_review_count = LoanClosureDocument.objects.filter(
        Q(parser_status__in=PARSER_REVIEW_STATUSES) | Q(verification_status__in=["pending", "rejected"])
    ).count()
    foreclosure_reconciliation_review_count = LoanForeclosureSnapshot.objects.exclude(
        reconciliation_status="full_match"
    ).count()
    foreclosure_pending_loan_count = loans.filter(status="foreclosure_pending").count()

    investment_count = Investment.objects.count()
    investment_assumption_count = Investment.objects.filter(Q(annual_return_rate__gt=0) | Q(monthly_sip__gt=0)).count()
    investment_import_review_count = InvestmentImportDocument.objects.filter(
        parser_status__in=PARSER_REVIEW_STATUSES
    ).count()

    vehicle_count = BikeProfile.objects.count()
    vehicle_value_count = BikeProfile.objects.filter(estimated_market_value__gt=0).count()
    heuristic_vehicle_value_count = BikeProfile.objects.filter(estimated_market_value__gt=0).exclude(
        verification_status="official"
    ).count()
    vehicle_import_review_count = BikeDocument.objects.filter(parser_status__in=PARSER_REVIEW_STATUSES).count()
    vehicle_actual_cost_missing_count = BikeIssueReport.objects.exclude(projected_cost__isnull=True).filter(
        projected_cost__gt=0,
        actual_cost__isnull=True,
    ).count()

    recruiter_jd_review_count = CareerJobAnalysis.objects.filter(parser_status__in=PARSER_REVIEW_STATUSES).count()
    career_resume_review_count = CareerResume.objects.filter(parser_status__in=PARSER_REVIEW_STATUSES).count()
    career_outcome_summary = career_opportunity_outcome_summary(CareerJobAnalysis.objects.all())
    salary_model_state = AdaptiveModelState.objects.filter(model_key="salary_predictor").first()
    salary_model_ready = bool(salary_model_state and salary_model_state.is_fresh)
    salary_outcomes_ready = bool(career_outcome_summary.get("maturity_status") == "mature")

    credit_report_review_count = CreditReportUpload.objects.filter(parser_status__in=PARSER_REVIEW_STATUSES).count()
    active_external_evidence = VerifiedExternalInsight.objects.filter(
        is_active=True,
        scope__in=EXTERNAL_CALCULATION_SCOPES,
    )
    stale_external_count = active_external_evidence.filter(
        Q(status__in=["stale", "failed", "rejected"]) | Q(stale_after__lte=now)
    ).count()
    due_external_count = int(refresh_health.get("due_records", stale_external_count) or 0)
    watchlist_external_count = int(refresh_health.get("watchlist_records", stale_external_count) or 0)
    scheduled_refresh_healthy = bool(refresh_health.get("scheduled_refresh_healthy", refresh_health.get("healthy", stale_external_count == 0)))

    manual_review_queues = [
        _queue("Statement imports", "statement_import_review", statement_review_count),
        _queue("Statement-linked transactions", "statement_transaction_review", unreviewed_statement_transactions),
        _queue("Loan repayment imports", "loan_repayment_review", loan_repayment_review_count),
        _queue("Loan import documents", "loan_import_review", loan_import_review_count),
        _queue("Loan closure documents", "loan_closure_review", loan_closure_review_count),
        _queue("Foreclosure reconciliation", "foreclosure_reconciliation_review", foreclosure_reconciliation_review_count),
        _queue("Investment import documents", "investment_import_review", investment_import_review_count),
        _queue("Vehicle import documents", "vehicle_import_review", vehicle_import_review_count),
        _queue("Resume imports", "resume_import_review", career_resume_review_count),
        _queue("Recruiter/JD imports", "recruiter_import_review", recruiter_jd_review_count),
        _queue("Credit report imports", "credit_report_review", credit_report_review_count),
    ]
    manual_review_queue_count = sum(item["count"] for item in manual_review_queues)
    document_review_count = sum(
        item["count"]
        for item in manual_review_queues
        if item["key"]
        in {
            "statement_import_review",
            "loan_import_review",
            "loan_closure_review",
            "investment_import_review",
            "vehicle_import_review",
            "resume_import_review",
            "recruiter_import_review",
            "credit_report_review",
        }
    )

    verified_calculations = [
        _entry(
            key="cash_flow_aggregation",
            label="Cash-flow aggregation",
            status="verified" if statement_review_count == 0 else "verified_formula_review_gated_data",
            progress=94 if statement_review_count == 0 else 84,
            code_path="apps/expenses/services/financial_intelligence.py::_build_monthly_buckets",
            evidence=[
                f"{transaction_count} transaction(s) grouped by transaction_date, direction, and classification",
                f"{imported_transaction_count} statement-derived transaction(s)",
            ],
            blockers=["Unreviewed statement imports can still distort buckets"] if statement_review_count else [],
        ),
        _entry(
            key="loan_balance_and_foreclosure_liability",
            label="Debt balance and foreclosure liability",
            status="verified" if loan_repayment_review_count == 0 and foreclosure_reconciliation_review_count == 0 else "review_gated",
            progress=90 if loan_repayment_review_count == 0 and foreclosure_reconciliation_review_count == 0 else 72,
            code_path="apps/expenses/services/financial_intelligence.py::_loan_reporting_balance",
            evidence=[
                f"{loan_count} loan(s)",
                f"{matched_loan_repayment_count} matched repayment(s)",
                f"{foreclosure_pending_loan_count} foreclosure-pending loan(s) kept in liabilities",
            ],
            blockers=[
                blocker
                for blocker in [
                    f"{loan_repayment_review_count} repayment row(s) need review" if loan_repayment_review_count else "",
                    f"{foreclosure_reconciliation_review_count} foreclosure snapshot(s) are not fully matched"
                    if foreclosure_reconciliation_review_count
                    else "",
                ]
                if blocker
            ],
        ),
        _entry(
            key="net_worth_balance_sheet",
            label="Net-worth balance sheet",
            status="verified_formula_with_vehicle_caveat" if heuristic_vehicle_value_count else "verified",
            progress=88 if heuristic_vehicle_value_count else 92,
            code_path="apps/expenses/services/financial_intelligence.py::_build_balance_sheet",
            evidence=[
                "Cash, credit liability, investment value, loan liability, home acquisition-cost proxy, and vehicle treatment are summed in one balance-sheet path",
                f"{vehicle_value_count} vehicle market value(s) present",
            ],
            blockers=["Some vehicle values are custom or AI-matched rather than official"] if heuristic_vehicle_value_count else [],
        ),
        _entry(
            key="investment_position_totals",
            label="Investment totals and gain/loss",
            status="verified" if investment_import_review_count == 0 else "review_gated",
            progress=91 if investment_import_review_count == 0 else 78,
            code_path="apps/investments/models.py::Investment.gain_loss",
            evidence=[f"{investment_count} investment position(s)"],
            blockers=[f"{investment_import_review_count} investment import document(s) need review"] if investment_import_review_count else [],
        ),
    ]

    review_gated_calculations = [
        _entry(
            key="loan_repayment_components",
            label="Loan repayment component totals",
            status="review_gated" if loan_repayment_review_count else "clear",
            progress=68 if loan_repayment_review_count else 88,
            code_path="apps/expenses/services/financial_intelligence.py::_build_loan_portfolio",
            evidence=[
                f"{loan_repayment_review_count} review repayment(s)",
                f"{matched_loan_repayment_count} matched repayment(s)",
            ],
            blockers=["Review queued repayments before trusting principal/interest component totals"]
            if loan_repayment_review_count
            else [],
        ),
        _entry(
            key="document_derived_imports",
            label="Document-derived imports",
            status="review_gated" if document_review_count else "clear",
            progress=66 if document_review_count else 88,
            code_path="apps/*/models.py::*ImportDocument and parser_status fields",
            evidence=[f"{document_review_count} parser-tracked document(s) need review"],
            blockers=["Clear parser review queues before treating document-derived money fields as verified"]
            if document_review_count
            else [],
        ),
        _entry(
            key="foreclosure_repayment_status",
            label="Loan foreclosure repayment status",
            status="review_gated" if foreclosure_reconciliation_review_count or loan_closure_review_count else "clear",
            progress=64 if foreclosure_reconciliation_review_count or loan_closure_review_count else 90,
            code_path="apps/loans/services/loan_foreclosure_service.py::reconcile_snapshot",
            evidence=[
                f"{foreclosure_reconciliation_review_count} non-full foreclosure reconciliation(s)",
                f"{loan_closure_review_count} closure document(s) pending or rejected",
            ],
            blockers=["Loan closure status must stay pending until a clean closure-payment match is accepted"]
            if foreclosure_reconciliation_review_count or loan_closure_review_count
            else [],
        ),
    ]

    heuristic_calculations = [
        _entry(
            key="investment_growth_projection",
            label="Investment growth projection",
            status="heuristic_assumption",
            progress=78 if investment_count else 82,
            code_path="apps/investments/views.py::_project_position_value",
            evidence=[
                f"{investment_assumption_count} position(s) use annual_return_rate or monthly_sip assumptions",
                "Projection compounds the current value and SIP monthly; it is not a guaranteed return model",
            ],
            blockers=["Validate projected growth against accepted portfolio outcomes before raising maturity"],
        ),
        _entry(
            key="risk_outlook_blend",
            label="Risk outlook score blend",
            status="heuristic_external_blend",
            progress=76 if stale_external_count else 82,
            code_path="apps/risk/services/risk_intelligence.py::RiskIntelligenceService.build_outlook",
            evidence=[
                "Manual risk snapshots, behavioral metrics, debt burden, mobility state, career fit, and external macro context are bounded together",
            ],
            blockers=["Risk score weights are deterministic heuristics, not a reviewed predictive risk model"],
        ),
        _entry(
            key="vehicle_valuation_treatment",
            label="Vehicle valuation and net-worth treatment",
            status="heuristic" if vehicle_count else "not_applicable",
            progress=74 if heuristic_vehicle_value_count or vehicle_actual_cost_missing_count else 86,
            code_path="apps/expenses/services/financial_intelligence.py::_build_vehicle_positions",
            evidence=[
                f"{vehicle_count} vehicle profile(s)",
                f"{heuristic_vehicle_value_count} non-official market value(s)",
                f"{vehicle_actual_cost_missing_count} projected issue cost(s) without actual-cost outcome",
            ],
            blockers=[
                blocker
                for blocker in [
                    "Vehicle value and asset/liability bucket depend on usage-pattern assumptions" if vehicle_count else "",
                    "Actual repair costs are still missing for projected vehicle issue costs"
                    if vehicle_actual_cost_missing_count
                    else "",
                ]
                if blocker
            ],
        ),
        _entry(
            key="career_salary_projection",
            label="Career salary projection",
            status="model_backed" if salary_model_ready and salary_outcomes_ready else "heuristic_fallback",
            progress=88 if salary_model_ready and salary_outcomes_ready else 72,
            code_path="apps/career/services/projection_engine.py::build_salary_projection",
            evidence=[
                f"salary model ready: {'yes' if salary_model_ready else 'no'}",
                f"{career_outcome_summary.get('validated_outcome_count', 0)} validated salary-bearing outcome(s)",
            ],
            blockers=[career_outcome_summary.get("blocker", "Salary outcome learning is not mature")]
            if not salary_outcomes_ready
            else [],
        ),
    ]

    external_data_sensitive_calculations = [
        _entry(
            key="risk_outlook_external_context",
            label="Risk outlook external context",
            status="fresh" if stale_external_count == 0 and scheduled_refresh_healthy else "stale_or_due",
            progress=84 if stale_external_count == 0 and scheduled_refresh_healthy else 68,
            code_path="apps/risk/services/risk_intelligence.py::build_outlook",
            evidence=[
                f"{active_external_evidence.count()} active calculation-relevant evidence record(s)",
                f"{stale_external_count} stale, failed, rejected, or due record(s)",
                f"{due_external_count} due record(s) from refresh health",
            ],
            blockers=["Refresh stale or due evidence before raising external-data-sensitive calculation maturity"]
            if stale_external_count or watchlist_external_count or not scheduled_refresh_healthy
            else [],
        ),
        _entry(
            key="investment_market_context",
            label="Investment market context",
            status="external_data_sensitive",
            progress=82 if stale_external_count == 0 else 70,
            code_path="apps/investments/views.py::_investment_summary_payload",
            evidence=["Portfolio views include market context and watchlist evidence when available"],
            blockers=["Market context remains sensitive to upstream freshness and source availability"],
        ),
        _entry(
            key="career_salary_market_context",
            label="Career salary and market context",
            status="external_data_sensitive",
            progress=80 if stale_external_count == 0 else 68,
            code_path="apps/career/services/projection_engine.py::build_growth_context",
            evidence=["Salary projection blends reported income/model output with macro and market context"],
            blockers=["Salary projection depends on fresh job, macro, and market evidence plus salary-bearing outcomes"],
        ),
    ]

    critical_path_progress = {
        "cash_flow": 94 if statement_review_count == 0 and unreviewed_statement_transactions == 0 else 82,
        "debt_and_repayment_status": 90
        if loan_repayment_review_count == 0 and foreclosure_reconciliation_review_count == 0 and loan_closure_review_count == 0
        else 68,
        "net_worth": 92 if heuristic_vehicle_value_count == 0 and foreclosure_pending_loan_count == 0 else 76,
        "investment_growth": 78 if investment_count else 82,
        "risk_outlook": 82 if stale_external_count == 0 and scheduled_refresh_healthy else 68,
        "vehicle_valuation": 86 if vehicle_count == 0 or (heuristic_vehicle_value_count == 0 and vehicle_actual_cost_missing_count == 0) else 72,
        "career_salary_projection": 88 if salary_model_ready and salary_outcomes_ready else 72,
        "document_derived_imports": 88 if document_review_count == 0 else 66,
    }
    overall_progress = _bounded_percent(mean(critical_path_progress.values()))

    blockers = []
    if loan_repayment_review_count:
        blockers.append(f"{loan_repayment_review_count} loan repayment import(s) still need manual review")
    if foreclosure_reconciliation_review_count or loan_closure_review_count:
        blockers.append("loan closure or foreclosure reconciliation still needs accepted proof")
    if document_review_count:
        blockers.append(f"{document_review_count} parser-tracked document import(s) still need review")
    if heuristic_vehicle_value_count:
        blockers.append(f"{heuristic_vehicle_value_count} vehicle market value(s) are custom or AI-matched")
    if vehicle_actual_cost_missing_count:
        blockers.append(f"{vehicle_actual_cost_missing_count} vehicle issue projection(s) still lack actual-cost outcome")
    if not salary_model_ready:
        blockers.append("salary projection is using fallback logic because the salary predictor is not fresh and ready")
    if not salary_outcomes_ready:
        blockers.append(career_outcome_summary.get("blocker", "salary-bearing outcome learning is not mature"))
    if stale_external_count or watchlist_external_count or not scheduled_refresh_healthy:
        blockers.append("external-data-sensitive calculations need fresh scheduled evidence proof")

    heuristic_dependency_count = len([item for item in heuristic_calculations if item["status"] != "not_applicable"])
    external_dependency_count = len(external_data_sensitive_calculations)
    return {
        "overall_progress": overall_progress,
        "maturity_status": "review_and_outcome_gated" if blockers else "verified_current_scope",
        "summary": (
            f"Calculation maturity is {overall_progress}% across cash flow, debt, net worth, investment growth, "
            f"risk outlook, vehicle valuation, salary projection, and document imports."
        ),
        "source_paths": [
            "apps/expenses/services/financial_intelligence.py",
            "apps/loans/services/loan_foreclosure_service.py",
            "apps/loans/services/payment_history_access.py",
            "apps/investments/views.py",
            "apps/risk/services/risk_intelligence.py",
            "apps/mobility/services/bike_service_intelligence.py",
            "apps/career/services/projection_engine.py",
            "apps/*/models.py parser_status/import fields",
        ],
        "critical_path_progress": {
            key: _bounded_percent(value)
            for key, value in critical_path_progress.items()
        },
        "manual_review_queues": manual_review_queues,
        "manual_review_queue_count": manual_review_queue_count,
        "manual_review_queues_left": [item for item in manual_review_queues if item["count"]],
        "document_review_count": document_review_count,
        "verified_calculations": verified_calculations,
        "review_gated_calculations": review_gated_calculations,
        "heuristic_calculations": heuristic_calculations,
        "external_data_sensitive_calculations": external_data_sensitive_calculations,
        "dependency_counts": {
            "review_gated": manual_review_queue_count,
            "heuristic_paths": heuristic_dependency_count,
            "external_data_sensitive_paths": external_dependency_count,
            "stale_or_due_external_records": stale_external_count,
            "watchlist_external_records": watchlist_external_count,
        },
        "salary_outcome_summary": career_outcome_summary,
        "external_data_health": {
            "active_records": active_external_evidence.count(),
            "stale_or_due_records": stale_external_count,
            "watchlist_records": watchlist_external_count,
            "due_records": due_external_count,
            "scheduled_refresh_healthy": scheduled_refresh_healthy,
        },
        "blockers": blockers,
    }
