from __future__ import annotations

from django.utils import timezone

from alfred_ai.internal_clock import clock_snapshot
from apps.reports.models import SystemTicket


class ReportingService:
    HIGH_SEVERITY_TERMS = (
        "security",
        "privacy",
        "breach",
        "unauthorized",
        "deleted",
        "data loss",
        "duplicate transaction",
        "wrong loan",
        "wrong lender",
        "wrong balance",
        "wrong account",
        "foreclosure",
        "cannot login",
        "500",
        "traceback",
        "crash",
        "payment missing",
        "statement mismatch",
        "corrupt",
        "exposed",
    )
    MEDIUM_SEVERITY_TERMS = (
        "parser",
        "parse",
        "upload",
        "sync",
        "stale",
        "not updating",
        "timeout",
        "slow",
        "chart",
        "layout",
        "verification",
        "review",
        "warning",
        "mismatch",
    )

    def create_system_ticket(self, *, user, module: str, title: str, summary: str, context_payload: dict | None = None) -> SystemTicket:
        normalized_context = dict(context_payload or {})
        created_clock = clock_snapshot()
        normalized_context["internal_clock"] = created_clock
        triage = self._triage_ticket(module=module, title=title, summary=summary, context_payload=normalized_context)
        normalized_context["triage"] = {
            "severity": triage["severity"],
            "handled_by": triage["handled_by"],
            "status": triage["status"],
            "reason": triage["reason"],
        }
        return SystemTicket.objects.create(
            user=user,
            module=module,
            title=title[:180],
            summary=summary.strip(),
            context_payload=normalized_context,
            status=triage["status"],
            severity=triage["severity"],
            handled_by=triage["handled_by"],
            resolution_summary=triage["resolution_summary"],
            resolved_at=timezone.now() if triage["status"] == "resolved" else None,
        )

    def _triage_ticket(self, *, module: str, title: str, summary: str, context_payload: dict) -> dict:
        requested_severity = str(context_payload.get("severity", "")).lower().strip()
        if requested_severity in {"low", "medium", "high"}:
            severity = requested_severity
            reason = "Severity was provided by the caller context."
        else:
            severity, reason = self._severity_from_text(module=module, title=title, summary=summary, context_payload=context_payload)

        if context_payload.get("requires_developer"):
            severity = "high"
            reason = "Developer escalation was requested by the caller context."

        if severity == "high":
            return {
                "severity": "high",
                "handled_by": "developer",
                "status": "open",
                "resolution_summary": "Escalated to the developer queue because the issue can affect correctness, account data, or core access.",
                "reason": reason,
            }

        return {
            "severity": severity,
            "handled_by": "alfred",
            "status": "resolved",
            "resolution_summary": self._resolution_copy(module=module, severity=severity),
            "reason": reason,
        }

    def _severity_from_text(self, *, module: str, title: str, summary: str, context_payload: dict) -> tuple[str, str]:
        text = " ".join(
            [
                module or "",
                title or "",
                summary or "",
                str(context_payload.get("reason", "")),
                str(context_payload.get("notes", "")),
            ]
        ).lower()

        if any(term in text for term in self.HIGH_SEVERITY_TERMS):
            return "high", "Detected high-risk keywords linked to correctness, security, or account-impacting failures."
        if module in {"expenses", "loans"} and any(term in text for term in ("wrong", "duplicate", "missing", "mismatch")):
            return "high", "Finance and loan data mismatches are routed to developers because they can affect financial correctness."
        if any(term in text for term in self.MEDIUM_SEVERITY_TERMS):
            return "medium", "Detected operational or parsing issues that ALFRED can auto-handle with safe guidance."
        return "low", "No high-risk keywords were detected, so the issue is treated as low severity."

    def _resolution_copy(self, *, module: str, severity: str) -> str:
        module_actions = {
            "expenses": "Verify the bank account selection and re-run the import only if the statement is new; duplicate fingerprints are already skipped for the same account.",
            "loans": "Re-check the selected loan and uploaded closure or statement document; low-confidence matches are isolated instead of mutating the loan book directly.",
            "career": "Refresh the resume or job link once and check the proof links; stale market feeds will refresh on the next scheduled cycle.",
            "mobility": "Upload a clearer vehicle document or service note with the vehicle profile selected so unrelated files can be rejected safely.",
            "risk": "Wait for the next verified refresh if the feed is stale, then compare the evidence links before acting on the signal.",
            "behavioral": "Reload the behavioral dashboard and submit a fresh entry; empty-state and duplicate-insight handling are already guarded.",
            "reports": "Re-open the page after a hard refresh; report generation metadata and ticket timestamps are server-stamped by ALFRED.",
            "general": "Retry once after a hard refresh. If the same issue repeats or affects money, account access, or data integrity, escalate it.",
        }
        action = module_actions.get(module, module_actions["general"])
        prefix = "ALFRED auto-handled this low-severity issue." if severity == "low" else "ALFRED auto-handled this medium-severity operational issue."
        return f"{prefix} {action}"


reporting_service = ReportingService()
