from __future__ import annotations

from collections import Counter
import hashlib
import json
import re

from django.utils import timezone

from alfred_ai.internal_clock import clock_snapshot
from apps.reports.models import OperationalLog, SystemTicket


class ChatGPTImportService:
    MAX_IMPORT_CHARS = 200_000
    MODULE_KEYWORDS = {
        "expenses": ("expense", "transaction", "merchant", "spend", "budget", "cash flow", "bank statement"),
        "loans": ("loan", "emi", "foreclosure", "repayment", "lender", "closure", "principal"),
        "investments": ("investment", "mutual fund", "nav", "portfolio", "stock", "asset allocation"),
        "credit": ("credit report", "cibil", "experian", "bureau", "tradeline", "credit score"),
        "career": ("resume", "job", "salary", "recruiter", "jd", "compensation", "interview"),
        "mobility": ("vehicle", "bike", "car", "service bill", "maintenance", "mileage", "route wear", "catalog"),
        "documents": ("ocr", "parser", "upload", "document", "invoice", "review queue", "correction"),
        "risk": ("risk", "insurance", "emergency", "layoff", "volatility", "freshness"),
        "tax": ("tax", "deduction", "regime", "80c", "itr", "tds"),
        "relationship": ("relationship", "partner", "family", "dependent", "shared goal"),
        "travel": ("travel", "trip", "route", "destination", "fuel stop", "itinerary"),
        "ml": ("model", "training", "ml", "supervised", "learning", "heuristic"),
    }

    ROLE_ALIASES = {
        "chatgpt": "assistant",
        "assistant": "assistant",
        "alfred": "assistant",
        "user": "user",
        "you": "user",
        "system": "system",
    }

    def build_payload(self, *, raw_text: str, title: str = "", import_type: str = "chat_transcript") -> dict:
        text = self._normalize_raw_text(raw_text)
        parsed_json = self._loads_json(text)
        messages = self._extract_messages_from_json(parsed_json) if parsed_json is not None else self._extract_messages_from_transcript(text)
        analysis_text = "\n".join(message["content"] for message in messages if message.get("content")).strip() or text
        detected_modules = self._detect_modules(analysis_text)
        roles = Counter(message.get("role") or "unknown" for message in messages)
        title_from_payload = self._title_from_json(parsed_json)
        source_kind = "chatgpt_json_export" if parsed_json is not None else "pasted_transcript"
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        summary = self._summary(analysis_text, detected_modules)
        line_count = len([line for line in text.splitlines() if line.strip()])

        return {
            "title": (title or title_from_payload or self._fallback_title(detected_modules)).strip()[:180],
            "import_type": import_type,
            "content_hash": content_hash,
            "parsed_payload": {
                "source_kind": source_kind,
                "summary": summary,
                "preview": self._preview(analysis_text),
                "detected_modules": detected_modules,
                "message_count": len(messages),
                "role_counts": dict(sorted(roles.items())),
                "line_count": line_count,
                "char_count": len(text),
                "word_count": len(re.findall(r"[A-Za-z0-9]+", analysis_text)),
                "suggested_next_steps": self._suggested_next_steps(detected_modules),
                "internal_clock": clock_snapshot(),
            },
        }

    def _normalize_raw_text(self, raw_text: str) -> str:
        text = str(raw_text or "").strip()
        if not text:
            raise ValueError("Paste a ChatGPT dashboard, transcript, or exported conversation JSON first.")
        if len(text) > self.MAX_IMPORT_CHARS:
            raise ValueError(f"ChatGPT imports are limited to {self.MAX_IMPORT_CHARS:,} characters per import.")
        return text

    def _loads_json(self, text: str):
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            return None

    def _extract_messages_from_json(self, payload) -> list[dict]:
        messages: list[dict] = []
        conversations = payload if isinstance(payload, list) else [payload]
        for item in conversations:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("mapping"), dict):
                messages.extend(self._messages_from_mapping(item["mapping"]))
            if isinstance(item.get("messages"), list):
                messages.extend(self._messages_from_list(item["messages"]))
            if isinstance(item.get("conversation"), list):
                messages.extend(self._messages_from_list(item["conversation"]))
        return messages

    def _messages_from_mapping(self, mapping: dict) -> list[dict]:
        extracted = []
        for node in mapping.values():
            message = node.get("message") if isinstance(node, dict) else None
            if not isinstance(message, dict):
                continue
            role = ((message.get("author") or {}).get("role") or "unknown").lower()
            content = self._content_to_text(message.get("content"))
            if content:
                extracted.append({"role": self.ROLE_ALIASES.get(role, role), "content": content})
        return extracted

    def _messages_from_list(self, messages: list) -> list[dict]:
        extracted = []
        for message in messages:
            if not isinstance(message, dict):
                continue
            author = message.get("author")
            role_value = author.get("role") if isinstance(author, dict) else author
            role = str(message.get("role") or role_value or "unknown").lower()
            content = self._content_to_text(message.get("content") or message.get("text") or message.get("message"))
            if content:
                extracted.append({"role": self.ROLE_ALIASES.get(role, role), "content": content})
        return extracted

    def _content_to_text(self, value) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            parts = value.get("parts")
            if isinstance(parts, list):
                return "\n".join(str(part) for part in parts if isinstance(part, (str, int, float))).strip()
            text = value.get("text")
            if isinstance(text, str):
                return text.strip()
        if isinstance(value, list):
            return "\n".join(self._content_to_text(item) for item in value).strip()
        return ""

    def _extract_messages_from_transcript(self, text: str) -> list[dict]:
        messages = []
        current_role = "unknown"
        current_lines: list[str] = []
        role_pattern = re.compile(r"^\s*(user|you|assistant|chatgpt|alfred|system)\s*[:\-]\s*(.*)$", re.IGNORECASE)
        for line in text.splitlines():
            match = role_pattern.match(line)
            if match:
                if current_lines:
                    messages.append({"role": current_role, "content": "\n".join(current_lines).strip()})
                current_role = self.ROLE_ALIASES.get(match.group(1).lower(), match.group(1).lower())
                current_lines = [match.group(2).strip()] if match.group(2).strip() else []
            elif line.strip():
                current_lines.append(line.rstrip())
        if current_lines:
            messages.append({"role": current_role, "content": "\n".join(current_lines).strip()})
        return messages

    def _detect_modules(self, text: str) -> list[dict]:
        lowered = text.lower()
        words = Counter(re.findall(r"[a-z0-9]+", lowered))
        modules = []
        for module, keywords in self.MODULE_KEYWORDS.items():
            score = 0
            matches = []
            for keyword in keywords:
                keyword = keyword.lower()
                if " " in keyword:
                    count = lowered.count(keyword)
                else:
                    count = words.get(keyword, 0)
                if count:
                    score += count
                    matches.append(keyword)
            if score:
                modules.append(
                    {
                        "module": module,
                        "score": score,
                        "confidence": round(min(0.95, 0.35 + score * 0.08), 2),
                        "matched_terms": matches[:6],
                    }
                )
        return sorted(modules, key=lambda item: (-item["score"], item["module"]))

    def _summary(self, text: str, detected_modules: list[dict]) -> str:
        module_names = [item["module"].replace("_", " ") for item in detected_modules[:4]]
        prefix = f"Detected context for {', '.join(module_names)}." if module_names else "No strong ALFRED module match was detected yet."
        return f"{prefix} {self._preview(text, limit=220)}".strip()

    def _preview(self, text: str, *, limit: int = 360) -> str:
        collapsed = re.sub(r"\s+", " ", text).strip()
        if len(collapsed) <= limit:
            return collapsed
        return f"{collapsed[: limit - 3].rstrip()}..."

    def _title_from_json(self, payload) -> str:
        if isinstance(payload, dict):
            title = payload.get("title") or payload.get("name")
            if isinstance(title, str):
                return title[:180]
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            title = payload[0].get("title") or payload[0].get("name")
            if isinstance(title, str):
                return title[:180]
        return ""

    def _fallback_title(self, detected_modules: list[dict]) -> str:
        if detected_modules:
            module = detected_modules[0]["module"].replace("_", " ").title()
            return f"ChatGPT {module} Context"
        return "ChatGPT Imported Context"

    def _suggested_next_steps(self, detected_modules: list[dict]) -> list[str]:
        if not detected_modules:
            return ["Review the imported text and map it manually to the right ALFRED workspace if needed."]
        return [
            f"Review {item['module'].replace('_', ' ')} signals before applying them to live records."
            for item in detected_modules[:4]
        ]


chatgpt_import_service = ChatGPTImportService()


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


class OperationalLoggingService:
    def log(
        self,
        *,
        user,
        module: str,
        event_type: str,
        message: str,
        category: str = "document",
        severity: str = "info",
        scope: str = "",
        document_id: int | None = None,
        file_name: str = "",
        payload: dict | None = None,
    ) -> OperationalLog:
        normalized_payload = dict(payload or {})
        normalized_payload["internal_clock"] = clock_snapshot()
        return OperationalLog.objects.create(
            user=user,
            module=module[:30] or "general",
            category=category,
            scope=scope[:50],
            event_type=event_type[:50] or "event",
            severity=severity,
            document_id=document_id,
            file_name=file_name[:255],
            message=message.strip(),
            payload=normalized_payload,
        )

    def recent_for_user(self, user, *, limit: int = 20, category: str | None = None) -> list[OperationalLog]:
        queryset = OperationalLog.objects.filter(user=user)
        if category:
            queryset = queryset.filter(category=category)
        return list(queryset.order_by("-created_at", "-id")[:limit])

    def serialize(self, entry: OperationalLog) -> dict:
        return {
            "id": entry.id,
            "module": entry.module,
            "category": entry.category,
            "scope": entry.scope,
            "event_type": entry.event_type,
            "severity": entry.severity,
            "document_id": entry.document_id,
            "file_name": entry.file_name,
            "message": entry.message,
            "payload": entry.payload or {},
            "created_at": entry.created_at.isoformat(),
        }


operational_logging_service = OperationalLoggingService()
