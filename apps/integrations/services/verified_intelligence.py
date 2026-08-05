from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone as datetime_timezone
import hashlib
import json
import re
from statistics import mean
from urllib.parse import quote_plus

import feedparser
import requests
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Max, Min, Q
from django.utils import timezone
from django.utils.text import slugify

from apps.integrations.models import VerifiedExternalInsight


@dataclass
class InsightResult:
    payload: dict
    evidence: dict
    cached: bool


JOB_SALARY_SNIPPET_RE = re.compile(
    r"(?:(?:INR|RS\.?|USD|\$)\s*)?\d[\d,]*(?:\.\d+)?\s*"
    r"(?:k|lpa|lakh|lakhs|crore|cr|million|m)?"
    r"(?:\s*(?:-|to)\s*(?:(?:INR|RS\.?|USD|\$)\s*)?\d[\d,]*(?:\.\d+)?\s*"
    r"(?:k|lpa|lakh|lakhs|crore|cr|million|m)?)?"
    r"\s*(?:per\s+annum|per\s+year|/year|yearly|annual|annum|lpa|per\s+month|/month|monthly|month|pm)?",
    re.IGNORECASE,
)


def _parse_stale_after(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


def freshness_snapshot(items: list[dict]) -> dict:
    active = [item for item in items if item]
    now = timezone.now()
    stale_after_values = []
    fresh_records = 0
    stale_or_due_records = 0
    missing_source_records = 0
    missing_freshness_records = 0
    for item in active:
        status = item.get("status") or ""
        stale_after = _parse_stale_after(item.get("stale_after"))
        if stale_after:
            stale_after_values.append(stale_after)
        elif status == "fresh":
            missing_freshness_records += 1
        if not item.get("source_url"):
            missing_source_records += 1
        is_due = bool(stale_after and stale_after <= now)
        if status == "fresh" and stale_after and not is_due:
            fresh_records += 1
        else:
            stale_or_due_records += 1
    next_stale_after = min(stale_after_values).isoformat() if stale_after_values else ""
    return {
        "tracked_records": len(active),
        "fresh_records": fresh_records,
        "stale_or_due_records": stale_or_due_records,
        "missing_source_records": missing_source_records,
        "missing_freshness_records": missing_freshness_records,
        "next_stale_after": next_stale_after,
        "proof_complete": bool(active)
        and fresh_records == len(active)
        and missing_source_records == 0
        and missing_freshness_records == 0,
    }


ADVISORY_PROOF_REQUIRED_FEATURES = (
    "source_url",
    "stale_after",
    "scheduled_refresh",
    "circuit_breaker",
    "stale_fallback",
)
ADVISORY_REFRESH_CONTRACT = {
    "scheduled_refresh": "refresh_due_records",
    "stale_after_required": True,
    "source_url_required": True,
    "circuit_breaker": True,
    "stale_fallback": True,
}
ADVISORY_PROOF_SURFACE_CONTRACTS = (
    {
        "key": "recommendation_overview",
        "label": "Recommendation overview",
        "surface_type": "recommendation",
        "payload_path": "apps.integrations.views._build_recommendation_overview_payload",
        "required_sources": ["Yahoo Finance", "World Bank"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "investment_summary",
        "label": "Investment summary and watchlist",
        "surface_type": "recommendation",
        "payload_path": "apps.investments.views._investment_summary_payload",
        "required_sources": ["Yahoo Finance", "World Bank"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "travel_advisor_preview",
        "label": "Travel advisor preview",
        "surface_type": "recommendation",
        "payload_path": "apps.mobility.services.travel_advisor.TravelAdvisorService.build_advice",
        "required_sources": ["OpenStreetMap Nominatim"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "risk_outlook",
        "label": "Risk outlook",
        "surface_type": "recommendation",
        "payload_path": "apps.risk.services.risk_intelligence.RiskIntelligenceService.build_outlook",
        "required_sources": ["World Bank"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "relationship_alignment",
        "label": "Relationship alignment",
        "surface_type": "relationship-adjacent",
        "payload_path": "apps.relationship.services.relationship_intelligence.build_relationship_alignment",
        "required_sources": ["Yahoo Finance", "World Bank"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "behavioral_fingerprint",
        "label": "Behavioral fingerprint",
        "surface_type": "relationship-adjacent",
        "payload_path": "apps.behavioral.services.build_behavioral_fingerprint",
        "required_sources": ["Yahoo Finance", "World Bank"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "behavioral_stress",
        "label": "Behavioral stress advisor",
        "surface_type": "relationship-adjacent",
        "payload_path": "apps.behavioral.services.build_behavioral_stress",
        "required_sources": ["Yahoo Finance", "World Bank"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "family_growth",
        "label": "Family growth planning",
        "surface_type": "relationship-adjacent",
        "payload_path": "apps.family.views._family_growth_payload",
        "required_sources": ["India Post", "NPS Trust"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
    {
        "key": "tax_optimizer",
        "label": "Tax optimizer",
        "surface_type": "recommendation",
        "payload_path": "apps.integrations.views._build_tax_optimizer_overview_payload",
        "required_sources": ["Income Tax Department", "India Post", "NPS Trust"],
        "contract_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
    },
)


def _normalize_evidence_items(evidence_items) -> list[dict]:
    if isinstance(evidence_items, dict):
        return [evidence_items]
    return [item for item in evidence_items or [] if isinstance(item, dict)]


def proof_contract_payload(*, evidence_items, freshness=None, required_sources=None, advisory_surface: str = "") -> dict:
    evidence = _normalize_evidence_items(evidence_items)
    freshness = freshness or freshness_snapshot(evidence)
    required_sources = list(required_sources or [])
    observed_sources = sorted(
        {
            str(item.get("source_name") or "").strip()
            for item in evidence
            if str(item.get("source_name") or "").strip()
        }
    )
    missing_required_sources = [source for source in required_sources if source not in observed_sources]
    return {
        "complete": bool(freshness.get("proof_complete")) and not missing_required_sources,
        "advisory_surface": advisory_surface,
        "required_sources": required_sources,
        "observed_sources": observed_sources,
        "tracked_records": freshness.get("tracked_records", 0),
        "fresh_records": freshness.get("fresh_records", 0),
        "stale_or_due_records": freshness.get("stale_or_due_records", 0),
        "missing_source_records": freshness.get("missing_source_records", 0),
        "missing_freshness_records": freshness.get("missing_freshness_records", 0),
        "missing_required_sources": missing_required_sources,
        "refresh_contract": dict(ADVISORY_REFRESH_CONTRACT),
    }


def advisory_proof_contract_snapshot() -> dict:
    surfaces = []
    for contract in ADVISORY_PROOF_SURFACE_CONTRACTS:
        contract_features = list(contract.get("contract_features", []))
        missing_features = [feature for feature in ADVISORY_PROOF_REQUIRED_FEATURES if feature not in contract_features]
        surfaces.append(
            {
                **contract,
                "missing_contract_features": missing_features,
                "complete": not missing_features,
            }
        )
    covered_surface_count = sum(1 for surface in surfaces if surface["complete"])
    return {
        "required_features": list(ADVISORY_PROOF_REQUIRED_FEATURES),
        "surface_count": len(surfaces),
        "covered_surface_count": covered_surface_count,
        "uncovered_surface_count": len(surfaces) - covered_surface_count,
        "scheduled_refresh": ADVISORY_REFRESH_CONTRACT["scheduled_refresh"],
        "healthy": covered_surface_count == len(surfaces),
        "new_signal_rule": "Do not add a new recommendation or relationship-adjacent signal unless it declares required sources, source URLs, stale-after deadlines, scheduled refresh, stale fallback, and circuit-breaker behavior.",
        "summary": (
            f"{covered_surface_count}/{len(surfaces)} recommendation or relationship-adjacent surface(s) declare the full proof contract."
        ),
        "surfaces": surfaces,
    }


def _iso_or_empty(value) -> str:
    return value.isoformat() if value else ""


class VerifiedIntelligenceService:
    USER_AGENT = "AlfredAI/1.0 (verified-intelligence)"
    CIRCUIT_FAILURE_THRESHOLD = 3
    CIRCUIT_OPEN_MINUTES = 20
    REFRESH_BATCH_SIZE = 25
    STALE_LOOKAHEAD_HOURS = 6

    def cleanup_stale(self, retention_days: int = 90) -> None:
        now = timezone.now()
        VerifiedExternalInsight.objects.filter(status="fresh", stale_after__lt=now).update(status="stale")
        VerifiedExternalInsight.objects.filter(
            status__in=["failed", "rejected"],
            verified_at__lt=now - timedelta(days=retention_days),
        ).delete()
        VerifiedExternalInsight.objects.filter(
            is_active=False,
            verified_at__lt=now - timedelta(days=retention_days),
        ).delete()

    def world_bank_indicator(self, indicator_code: str, title: str, stale_days: int = 30, *, force: bool = False) -> InsightResult:
        endpoint = f"https://api.worldbank.org/v2/country/IND/indicator/{indicator_code}"
        cache_key = f"world-bank:{indicator_code}"
        return self._use_or_refresh(
            scope="macro",
            cache_key=cache_key,
            title=title,
            source_name="World Bank",
            source_url=f"{endpoint}?format=json&per_page=8",
            ttl=timedelta(days=stale_days),
            fetcher=lambda: self._fetch_world_bank(endpoint, title),
            force=force,
        )

    def market_snapshot(self, stale_hours: int = 12, *, force: bool = False) -> InsightResult:
        return self._use_or_refresh(
            scope="market",
            cache_key="india-equity-volatility",
            title="India Market Snapshot",
            source_name="Yahoo Finance",
            source_url="https://finance.yahoo.com/quote/%5ENSEI/",
            ttl=timedelta(hours=stale_hours),
            fetcher=self._fetch_market_snapshot,
            force=force,
        )

    def geocode_destination(self, destination: str, stale_days: int = 30, *, force: bool = False) -> InsightResult:
        slug = slugify(destination) or "destination"
        source_url = "https://nominatim.openstreetmap.org/search"
        return self._use_or_refresh(
            scope="travel",
            cache_key=f"geocode:{slug}",
            title=f"Destination match for {destination}",
            source_name="OpenStreetMap Nominatim",
            source_url=source_url,
            ttl=timedelta(days=stale_days),
            query=destination,
            fetcher=lambda: self._fetch_geocode(destination),
            force=force,
        )

    def offbeat_suggestions(self, destination: str, stale_days: int = 14, *, force: bool = False) -> InsightResult:
        slug = slugify(destination) or "destination"
        source_url = "https://nominatim.openstreetmap.org/search"
        return self._use_or_refresh(
            scope="travel",
            cache_key=f"offbeat:{slug}",
            title=f"Offbeat suggestions near {destination}",
            source_name="OpenStreetMap Nominatim",
            source_url=source_url,
            ttl=timedelta(days=stale_days),
            query=destination,
            fetcher=lambda: self._fetch_offbeat(destination),
            force=force,
        )

    def weather_snapshot(self, latitude: float, longitude: float, start_date: date, end_date: date, stale_hours: int = 8, *, force: bool = False) -> InsightResult:
        cache_key = f"weather:{latitude:.3f}:{longitude:.3f}:{start_date.isoformat()}:{end_date.isoformat()}"
        source_url = "https://api.open-meteo.com/v1/forecast"
        return self._use_or_refresh(
            scope="travel",
            cache_key=cache_key,
            title=f"Weather forecast {start_date.isoformat()} to {end_date.isoformat()}",
            source_name="Open-Meteo",
            source_url=source_url,
            ttl=timedelta(hours=stale_hours),
            fetcher=lambda: self._fetch_weather(latitude, longitude, start_date, end_date),
            force=force,
        )

    def google_news_search(self, query: str, stale_hours: int = 8, *, force: bool = False) -> InsightResult:
        slug = slugify(query)[:120] or "news"
        feed_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        return self._use_or_refresh(
            scope="news",
            cache_key=f"google-news:{slug}",
            title=f"Google News search for {query}",
            source_name="Google News RSS",
            source_url=feed_url,
            ttl=timedelta(hours=stale_hours),
            query=query,
            fetcher=lambda: self._fetch_google_news(feed_url, query),
            force=force,
        )

    def remotive_jobs(self, search_term: str, stale_hours: int = 8, *, force: bool = False) -> InsightResult:
        slug = slugify(search_term)[:120] or "jobs"
        source_url = "https://remotive.com/api/remote-jobs"
        return self._use_or_refresh(
            scope="jobs",
            cache_key=f"remotive:{slug}",
            title=f"Remotive job search for {search_term}",
            source_name="Remotive Jobs API",
            source_url=source_url,
            ttl=timedelta(hours=stale_hours),
            query=search_term,
            fetcher=lambda: self._fetch_remotive_jobs(search_term),
            force=force,
        )

    def arbeitnow_jobs(self, search_term: str, stale_hours: int = 8, *, force: bool = False) -> InsightResult:
        slug = slugify(search_term)[:120] or "jobs"
        source_url = "https://www.arbeitnow.com/api/job-board-api"
        return self._use_or_refresh(
            scope="jobs",
            cache_key=f"arbeitnow:{slug}",
            title=f"Arbeitnow job search for {search_term}",
            source_name="Arbeitnow Job Board API",
            source_url=source_url,
            ttl=timedelta(hours=stale_hours),
            query=search_term,
            fetcher=lambda: self._fetch_arbeitnow_jobs(search_term),
            force=force,
        )

    def remoteok_jobs(self, search_term: str, stale_hours: int = 8, *, force: bool = False) -> InsightResult:
        slug = slugify(search_term)[:120] or "jobs"
        source_url = "https://remoteok.com/api"
        return self._use_or_refresh(
            scope="jobs",
            cache_key=f"remoteok:{slug}",
            title=f"Remote OK job search for {search_term}",
            source_name="Remote OK API",
            source_url=source_url,
            ttl=timedelta(hours=stale_hours),
            query=search_term,
            fetcher=lambda: self._fetch_remoteok_jobs(search_term),
            force=force,
        )

    def tax_regime_reference(self, stale_days: int = 45, *, force: bool = False) -> InsightResult:
        return self._static_reference(
            scope="tax",
            cache_key="india-income-tax-regimes",
            title="India income tax regime reference",
            source_name="Income Tax Department",
            source_url="https://www.incometax.gov.in/iec/foportal/",
            ttl=timedelta(days=stale_days),
            payload={
                "assessment_year": "2026-27",
                "old_regime_basic_exemption": 250000,
                "new_regime_basic_exemption": 300000,
                "standard_deduction_old": 50000,
                "standard_deduction_new": 75000,
            },
            summary="Official income tax regime reference payload for current slab and standard-deduction comparisons.",
            notes="This record is source-backed and refreshed on a slower cadence because tax slab references do not change intraday.",
            force=force,
        )

    def nps_tax_reference(self, stale_days: int = 45, *, force: bool = False) -> InsightResult:
        return self._static_reference(
            scope="tax",
            cache_key="india-nps-tax-benefit",
            title="NPS tax benefit reference",
            source_name="NPS Trust",
            source_url="https://npstrust.org.in/",
            ttl=timedelta(days=stale_days),
            payload={
                "section": "80CCD(1B)",
                "additional_limit": 50000,
                "instrument": "National Pension System",
            },
            summary="Official NPS Trust reference for additional 80CCD(1B) tax-benefit tracking.",
            notes="Use this as a policy reference only; final eligibility still depends on the user's filed tax profile.",
            force=force,
        )

    def ppf_reference(self, stale_days: int = 45, *, force: bool = False) -> InsightResult:
        return self._static_reference(
            scope="tax",
            cache_key="india-ppf-reference",
            title="PPF contribution reference",
            source_name="India Post",
            source_url="https://www.indiapost.gov.in/Financial/pages/content/post-office-saving-schemes.aspx",
            ttl=timedelta(days=stale_days),
            payload={
                "instrument": "Public Provident Fund",
                "section": "80C",
                "annual_limit": 150000,
            },
            summary="Official India Post reference for PPF contribution treatment under long-term tax-saving planning.",
            notes="PPF is tracked here as an official reference input for Alfred's deduction catalog and planning guidance.",
            force=force,
        )

    def macro_context(self) -> dict:
        unemployment = self.world_bank_indicator("SL.UEM.TOTL.ZS", "India unemployment rate")
        inflation = self.world_bank_indicator("FP.CPI.TOTL.ZG", "India inflation rate")
        market = self.market_snapshot()

        payload = {
            "unemployment": unemployment.payload,
            "inflation": inflation.payload,
            "market": market.payload,
        }

        evidence = [unemployment.evidence, inflation.evidence, market.evidence]
        return {"payload": payload, "evidence": evidence}

    def household_planning_context(self) -> dict:
        inflation = self.world_bank_indicator("FP.CPI.TOTL.ZG", "India inflation rate")
        market = self.market_snapshot()
        evidence = [inflation.evidence, market.evidence]
        return {
            "payload": {
                "inflation": inflation.payload,
                "market": market.payload,
            },
            "evidence": evidence,
            "freshness": freshness_snapshot(evidence),
            "notes": [
                "Household planning context is source-backed by inflation and market-volatility evidence.",
                "External evidence is used only to contextualize affordability and decision pressure.",
            ],
        }

    def _static_reference(
        self,
        *,
        scope: str,
        cache_key: str,
        title: str,
        source_name: str,
        source_url: str,
        ttl: timedelta,
        payload: dict,
        summary: str,
        notes: str,
        force: bool = False,
    ) -> InsightResult:
        return self._use_or_refresh(
            scope=scope,
            cache_key=cache_key,
            title=title,
            source_name=source_name,
            source_url=source_url,
            ttl=ttl,
            fetcher=lambda: (payload, summary, notes),
            force=force,
        )

    def _use_or_refresh(self, scope: str, cache_key: str, title: str, source_name: str, source_url: str, ttl: timedelta, fetcher, query: str = "", force: bool = False) -> InsightResult:
        self.cleanup_stale()
        record = (
            VerifiedExternalInsight.objects.filter(scope=scope, cache_key=cache_key, source_url=source_url, is_active=True)
            .order_by("-verified_at", "-id")
            .first()
        )
        if record and record.is_fresh and not force:
            return InsightResult(record.payload, self._serialize_evidence(record), True)

        if self._circuit_is_open(scope, cache_key, source_url):
            note = self._circuit_note(scope, cache_key, source_url)
            if record:
                if record.status == "fresh":
                    record.status = "stale"
                self._record_refresh_observation(
                    record,
                    "skipped",
                    note,
                    record_status=record.status,
                )
                return InsightResult(record.payload, self._serialize_evidence(record, note), True)
            return InsightResult(
                {},
                self._synthetic_evidence(title, source_name, source_url, query, "failed", f"{title} refresh is paused by the circuit breaker.", note),
                True,
            )

        try:
            payload, summary, notes = fetcher()
        except Exception as exc:
            breaker_state = self._record_circuit_failure(scope, cache_key, source_url, str(exc))
            breaker_note = self._circuit_state_message(breaker_state)
            if record:
                if record.status == "fresh":
                    record.status = "stale"
                self._record_refresh_observation(
                    record,
                    "failed",
                    f"{exc} {breaker_note}".strip(),
                    record_status=record.status,
                )
                return InsightResult(record.payload, self._serialize_evidence(record, breaker_note), True)
            failed = self._store(
                scope=scope,
                cache_key=cache_key,
                title=title,
                source_name=source_name,
                source_url=source_url,
                query=query,
                payload={"error": str(exc)},
                summary=f"{title} could not be refreshed.",
                ttl=ttl,
                status="failed",
                notes=f"{exc} {breaker_note}".strip(),
            )
            return InsightResult({}, self._serialize_evidence(failed), False)

        self._clear_circuit(scope, cache_key, source_url)
        stored = self._store(
            scope=scope,
            cache_key=cache_key,
            title=title,
            source_name=source_name,
            source_url=source_url,
            query=query,
            payload=payload,
            summary=summary,
            ttl=ttl,
            status="fresh",
            notes=notes,
        )
        return InsightResult(payload, self._serialize_evidence(stored), False)

    def refresh_due_records(self, batch_size: int | None = None) -> dict:
        self.cleanup_stale()
        now = timezone.now()
        batch_size = batch_size or self.REFRESH_BATCH_SIZE
        health_before = self.refresh_health_snapshot(now=now)
        candidates = list(
            VerifiedExternalInsight.objects.filter(is_active=True)
            .filter(Q(status="stale") | Q(stale_after__lte=now + timedelta(hours=self.STALE_LOOKAHEAD_HOURS)))
            .order_by("stale_after", "-verified_at", "-id")[:batch_size]
        )

        processed = 0
        refreshed = 0
        skipped = 0
        failed = 0
        seen = set()
        per_scope = {}
        records = []
        for record in candidates:
            key = (record.scope, record.cache_key, record.source_url)
            if key in seen:
                skipped += 1
                self._record_refresh_observation(
                    record,
                    "skipped",
                    "Duplicate active source record skipped within the same refresh batch.",
                )
                self._increment_refresh_scope(per_scope, record.scope, "skipped", processed=False)
                records.append(self._refresh_record_outcome(record, "skipped", "duplicate_source"))
                continue
            seen.add(key)
            processed += 1
            outcome = self._refresh_record(record)
            if outcome == "refreshed":
                refreshed += 1
            elif outcome == "skipped":
                skipped += 1
            else:
                failed += 1
            self._increment_refresh_scope(per_scope, record.scope, outcome)
            records.append(self._refresh_record_outcome(record, outcome))

        health_after = self.refresh_health_snapshot()

        return {
            "processed": processed,
            "refreshed": refreshed,
            "skipped": skipped,
            "failed": failed,
            "batch_size": batch_size,
            "started_at": now.isoformat(),
            "completed_at": timezone.now().isoformat(),
            "watchlist_before": health_before["watchlist_records"],
            "watchlist_after": health_after["watchlist_records"],
            "last_refresh_attempt_at": health_after["last_refresh_attempt_at"],
            "last_refresh_success_at": health_after["last_refresh_success_at"],
            "per_scope": [per_scope[key] for key in sorted(per_scope)],
            "records": records,
        }

    def refresh_health_snapshot(self, now=None) -> dict:
        now = now or timezone.now()
        active = VerifiedExternalInsight.objects.filter(is_active=True)
        watchlist_filter = Q(status__in=["stale", "failed", "rejected"]) | Q(stale_after__lte=now)
        watchlist = active.filter(watchlist_filter)
        fresh = active.filter(status="fresh", stale_after__gt=now)
        due = active.filter(status="fresh", stale_after__lte=now)
        status_counts = {item["status"]: item["count"] for item in active.values("status").annotate(count=Count("id"))}

        last_attempt = active.exclude(last_refresh_attempt_at__isnull=True).aggregate(value=Max("last_refresh_attempt_at"))["value"]
        last_success = active.exclude(last_refresh_success_at__isnull=True).aggregate(value=Max("last_refresh_success_at"))["value"]
        legacy_success = fresh.aggregate(value=Max("verified_at"))["value"]
        if legacy_success and (not last_success or legacy_success > last_success):
            last_success = legacy_success

        per_scope = []
        for scope in sorted(active.order_by().values_list("scope", flat=True).distinct()):
            scoped = active.filter(scope=scope)
            scoped_watchlist = scoped.filter(watchlist_filter)
            scoped_fresh = scoped.filter(status="fresh", stale_after__gt=now)
            scope_last_attempt = scoped.exclude(last_refresh_attempt_at__isnull=True).aggregate(value=Max("last_refresh_attempt_at"))["value"]
            scope_last_success = scoped.exclude(last_refresh_success_at__isnull=True).aggregate(value=Max("last_refresh_success_at"))["value"]
            scope_legacy_success = scoped_fresh.aggregate(value=Max("verified_at"))["value"]
            if scope_legacy_success and (not scope_last_success or scope_legacy_success > scope_last_success):
                scope_last_success = scope_legacy_success
            per_scope.append(
                {
                    "scope": scope,
                    "active_records": scoped.count(),
                    "fresh_records": scoped_fresh.count(),
                    "watchlist_records": scoped_watchlist.count(),
                    "due_records": scoped.filter(status="fresh", stale_after__lte=now).count(),
                    "stale_records": scoped.filter(status="stale").count(),
                    "failed_records": scoped.filter(status="failed").count(),
                    "rejected_records": scoped.filter(status="rejected").count(),
                    "last_refresh_attempt_at": _iso_or_empty(scope_last_attempt),
                    "last_refresh_success_at": _iso_or_empty(scope_last_success),
                }
            )

        next_due_at = fresh.aggregate(value=Min("stale_after"))["value"]
        oldest_watchlist_at = watchlist.aggregate(value=Min("stale_after"))["value"]
        active_count = active.count()
        watchlist_count = watchlist.count()
        return {
            "active_records": active_count,
            "fresh_records": fresh.count(),
            "watchlist_records": watchlist_count,
            "due_records": due.count(),
            "stale_records": status_counts.get("stale", 0),
            "failed_records": status_counts.get("failed", 0),
            "rejected_records": status_counts.get("rejected", 0),
            "last_refresh_attempt_at": _iso_or_empty(last_attempt),
            "last_refresh_success_at": _iso_or_empty(last_success),
            "next_due_at": _iso_or_empty(next_due_at),
            "oldest_watchlist_stale_after": _iso_or_empty(oldest_watchlist_at),
            "per_scope": per_scope,
            "healthy": active_count > 0 and watchlist_count == 0,
            "summary": (
                f"{fresh.count()}/{active_count} active evidence record(s) are fresh; "
                f"{watchlist_count} stale, failed, rejected, or due record(s) are on the watchlist."
            ),
        }

    def guardrail_snapshot(self) -> dict:
        proof_contract = advisory_proof_contract_snapshot()
        refresh_health = self.refresh_health_snapshot()
        return {
            "circuit_failure_threshold": self.CIRCUIT_FAILURE_THRESHOLD,
            "circuit_open_minutes": self.CIRCUIT_OPEN_MINUTES,
            "refresh_batch_size": self.REFRESH_BATCH_SIZE,
            "stale_lookahead_hours": self.STALE_LOOKAHEAD_HOURS,
            "proof_contract": proof_contract,
            "refresh_health": refresh_health,
            "fault_tolerance": [
                "Repeated upstream failures trip a circuit breaker before more external calls are attempted.",
                "If a verified record already exists, Alfred falls back to the latest stored payload instead of failing the dashboard outright.",
                "Scheduled refresh is batch-limited so one bad source cannot overload the whole refresh cycle.",
                "Refresh health exposes processed, refreshed, skipped, failed, per-scope watchlist, last-attempt, and last-success outcomes.",
                "Stale cleanup only removes failed or inactive records after retention windows instead of deleting active evidence aggressively.",
                proof_contract["new_signal_rule"],
            ],
        }

    @transaction.atomic
    def _store(
        self,
        scope: str,
        cache_key: str,
        title: str,
        source_name: str,
        source_url: str,
        query: str,
        payload: dict,
        summary: str,
        ttl: timedelta,
        status: str,
        notes: str,
    ) -> VerifiedExternalInsight:
        checksum = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        VerifiedExternalInsight.objects.filter(scope=scope, cache_key=cache_key, source_url=source_url, is_active=True).update(is_active=False)
        now = timezone.now()
        return VerifiedExternalInsight.objects.create(
            scope=scope,
            cache_key=cache_key,
            title=title,
            source_name=source_name,
            source_url=source_url,
            query=query,
            summary=summary,
            payload=payload,
            checksum=checksum,
            status=status,
            fetched_at=now,
            verified_at=now,
            stale_after=now + ttl,
            last_refresh_attempt_at=now,
            last_refresh_success_at=now if status == "fresh" else None,
            last_refresh_status="refreshed" if status == "fresh" else status,
            last_refresh_error="" if status == "fresh" else notes[:1000],
            notes=notes,
            is_active=True,
        )

    def _serialize_evidence(self, record: VerifiedExternalInsight, extra_note: str = "") -> dict:
        return {
            "title": record.title,
            "source_name": record.source_name,
            "source_url": record.source_url,
            "summary": record.summary,
            "status": record.status,
            "fetched_at": record.fetched_at.isoformat(),
            "verified_at": record.verified_at.isoformat(),
            "stale_after": record.stale_after.isoformat(),
            "last_refresh_attempt_at": _iso_or_empty(record.last_refresh_attempt_at),
            "last_refresh_success_at": _iso_or_empty(record.last_refresh_success_at),
            "last_refresh_status": record.last_refresh_status,
            "last_refresh_error": record.last_refresh_error,
            "query": record.query,
            "notes": " ".join(part for part in [record.notes, extra_note] if part).strip(),
        }

    def _synthetic_evidence(self, title: str, source_name: str, source_url: str, query: str, status: str, summary: str, notes: str = "") -> dict:
        return {
            "title": title,
            "source_name": source_name,
            "source_url": source_url,
            "summary": summary,
            "status": status,
            "fetched_at": "",
            "verified_at": "",
            "stale_after": "",
            "last_refresh_attempt_at": "",
            "last_refresh_success_at": "",
            "last_refresh_status": status,
            "last_refresh_error": notes,
            "query": query,
            "notes": notes,
        }

    def _refresh_record(self, record: VerifiedExternalInsight) -> str:
        try:
            if record.scope == "macro" and record.cache_key.startswith("world-bank:"):
                indicator = record.cache_key.split(":", 1)[1]
                return self._run_refresh_adapter(record, lambda: self.world_bank_indicator(indicator, record.title, force=True))
            if record.scope == "market" and record.cache_key == "india-equity-volatility":
                return self._run_refresh_adapter(record, lambda: self.market_snapshot(force=True))
            if record.scope == "travel" and record.cache_key.startswith("geocode:") and record.query:
                return self._run_refresh_adapter(record, lambda: self.geocode_destination(record.query, force=True))
            if record.scope == "travel" and record.cache_key.startswith("offbeat:") and record.query:
                return self._run_refresh_adapter(record, lambda: self.offbeat_suggestions(record.query, force=True))
            if record.scope == "travel" and record.cache_key.startswith("weather:"):
                _, latitude, longitude, start_date, end_date = record.cache_key.split(":")
                return self._run_refresh_adapter(
                    record,
                    lambda: self.weather_snapshot(float(latitude), float(longitude), date.fromisoformat(start_date), date.fromisoformat(end_date), force=True),
                )
            if record.scope == "news" and record.query:
                return self._run_refresh_adapter(record, lambda: self.google_news_search(record.query, force=True))
            if record.scope == "jobs" and record.query:
                if record.cache_key.startswith("arbeitnow:"):
                    return self._run_refresh_adapter(record, lambda: self.arbeitnow_jobs(record.query, force=True))
                elif record.cache_key.startswith("remoteok:"):
                    return self._run_refresh_adapter(record, lambda: self.remoteok_jobs(record.query, force=True))
                return self._run_refresh_adapter(record, lambda: self.remotive_jobs(record.query, force=True))
            if record.scope == "tax" and record.cache_key == "india-income-tax-regimes":
                return self._run_refresh_adapter(record, lambda: self.tax_regime_reference(force=True))
            if record.scope == "tax" and record.cache_key == "india-nps-tax-benefit":
                return self._run_refresh_adapter(record, lambda: self.nps_tax_reference(force=True))
            if record.scope == "tax" and record.cache_key == "india-ppf-reference":
                return self._run_refresh_adapter(record, lambda: self.ppf_reference(force=True))
        except Exception as exc:
            fallback_status = "stale" if record.status == "fresh" else record.status
            self._record_refresh_observation(record, "failed", str(exc), record_status=fallback_status)
            return "failed"
        self._record_refresh_observation(record, "skipped", "No refresh adapter is registered for this evidence record.")
        return "skipped"

    def _run_refresh_adapter(self, record: VerifiedExternalInsight, refresh_call) -> str:
        try:
            result = refresh_call()
        except Exception as exc:
            fallback_status = "stale" if record.status == "fresh" else record.status
            self._record_refresh_observation(record, "failed", str(exc), record_status=fallback_status)
            return "failed"
        outcome, note = self._refresh_outcome_from_result(result)
        if outcome == "refreshed":
            self._record_refresh_observation(record, "refreshed", "", success=True)
        elif outcome == "skipped":
            self._record_refresh_observation(record, "skipped", note)
        else:
            fallback_status = "stale" if record.status == "fresh" else record.status
            self._record_refresh_observation(record, "failed", note, record_status=fallback_status)
        return outcome

    def _refresh_outcome_from_result(self, result) -> tuple[str, str]:
        if not isinstance(result, InsightResult):
            return "refreshed", ""
        evidence = result.evidence or {}
        status = evidence.get("status") or ""
        notes = evidence.get("notes") or evidence.get("summary") or ""
        if status == "fresh":
            return ("skipped" if result.cached else "refreshed"), notes
        if "circuit breaker" in notes.lower() or "paused by the circuit" in notes.lower():
            return "skipped", notes
        return "failed", notes

    def _record_refresh_observation(
        self,
        record: VerifiedExternalInsight,
        refresh_status: str,
        error_message: str = "",
        *,
        success: bool = False,
        record_status: str | None = None,
    ) -> None:
        now = timezone.now()
        record.last_refresh_attempt_at = now
        record.last_refresh_status = refresh_status[:32]
        record.last_refresh_error = "" if refresh_status == "refreshed" else (error_message or "")[:1000]
        update_fields = ["last_refresh_attempt_at", "last_refresh_status", "last_refresh_error"]
        if success:
            record.last_refresh_success_at = now
            update_fields.append("last_refresh_success_at")
        if record_status:
            record.status = record_status
            update_fields.append("status")
        record.save(update_fields=update_fields)

    def _increment_refresh_scope(self, per_scope: dict, scope: str, outcome: str, *, processed: bool = True) -> None:
        bucket = per_scope.setdefault(
            scope,
            {
                "scope": scope,
                "processed": 0,
                "refreshed": 0,
                "skipped": 0,
                "failed": 0,
            },
        )
        if processed:
            bucket["processed"] += 1
        if outcome == "refreshed":
            bucket["refreshed"] += 1
        elif outcome == "failed":
            bucket["failed"] += 1
        elif outcome == "skipped":
            bucket["skipped"] += 1
        else:
            bucket["failed"] += 1

    def _refresh_record_outcome(self, record: VerifiedExternalInsight, outcome: str, reason: str = "") -> dict:
        return {
            "id": record.id,
            "scope": record.scope,
            "cache_key": record.cache_key,
            "source_name": record.source_name,
            "status": outcome,
            "reason": reason or record.last_refresh_error,
        }

    def _circuit_cache_key(self, scope: str, cache_key: str, source_url: str) -> str:
        digest = hashlib.sha256(f"{scope}|{cache_key}|{source_url}".encode("utf-8")).hexdigest()[:24]
        return f"verified-intelligence:circuit:{digest}"

    def _read_circuit(self, scope: str, cache_key: str, source_url: str) -> dict:
        return cache.get(self._circuit_cache_key(scope, cache_key, source_url), {}) or {}

    def _clear_circuit(self, scope: str, cache_key: str, source_url: str) -> None:
        cache.delete(self._circuit_cache_key(scope, cache_key, source_url))

    def _circuit_is_open(self, scope: str, cache_key: str, source_url: str) -> bool:
        state = self._read_circuit(scope, cache_key, source_url)
        opened_until = state.get("opened_until")
        if not opened_until:
            return False
        return timezone.now() < datetime.fromisoformat(opened_until)

    def _record_circuit_failure(self, scope: str, cache_key: str, source_url: str, error_message: str) -> dict:
        state = self._read_circuit(scope, cache_key, source_url)
        failures = int(state.get("failure_count", 0)) + 1
        opened_until = ""
        if failures >= self.CIRCUIT_FAILURE_THRESHOLD:
            opened_until = (timezone.now() + timedelta(minutes=self.CIRCUIT_OPEN_MINUTES)).isoformat()
        updated = {
            "failure_count": failures,
            "opened_until": opened_until,
            "last_error": error_message[:300],
            "updated_at": timezone.now().isoformat(),
        }
        timeout_seconds = max(self.CIRCUIT_OPEN_MINUTES * 60, 3600)
        cache.set(self._circuit_cache_key(scope, cache_key, source_url), updated, timeout=timeout_seconds)
        return updated

    def _circuit_state_message(self, state: dict) -> str:
        if state.get("opened_until"):
            return f"Circuit breaker is open until {state['opened_until']} after {state.get('failure_count', 0)} consecutive failures."
        return f"Failure count for this source is now {state.get('failure_count', 0)}."

    def _circuit_note(self, scope: str, cache_key: str, source_url: str) -> str:
        state = self._read_circuit(scope, cache_key, source_url)
        if not state:
            return ""
        return self._circuit_state_message(state)

    def _fetch_world_bank(self, endpoint: str, title: str) -> tuple[dict, str, str]:
        response = requests.get(
            endpoint,
            params={"format": "json", "per_page": 8},
            headers={"User-Agent": self.USER_AGENT},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        series = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
        items = [{"year": row.get("date"), "value": row.get("value")} for row in series if row.get("value") is not None]
        latest = items[0] if items else {"year": "", "value": None}
        summary = f"{title} latest available India value is {latest['value']} for {latest['year']}."
        return {
            "latest_year": latest["year"],
            "latest_value": latest["value"],
            "series": items[:5],
        }, summary, "Indicator is cached from the World Bank API and marked stale after the configured freshness window."

    def _fetch_market_snapshot(self) -> tuple[dict, str, str]:
        nifty_history = self._fetch_yahoo_chart("%5ENSEI", range_value="3mo", interval="1d")
        vix_history = self._fetch_yahoo_chart("%5EINDIAVIX", range_value="1mo", interval="1d")
        close = nifty_history["close"]
        if not close:
            raise ValueError("NIFTY 50 history is unavailable.")

        latest = float(close[-1])
        month_ago = float(close[max(len(close) - 22, 0)])
        month_return = round(((latest - month_ago) / month_ago) * 100, 2) if month_ago else 0
        pct_changes = []
        for idx in range(1, len(close)):
            previous = close[idx - 1]
            current = close[idx]
            if previous:
                pct_changes.append((current - previous) / previous)
        tail = pct_changes[-20:]
        if tail:
            avg = sum(tail) / len(tail)
            variance = sum((item - avg) ** 2 for item in tail) / len(tail)
            realized_vol = round((variance ** 0.5) * (252 ** 0.5) * 100, 2)
        else:
            realized_vol = None
        vix_close = vix_history["close"]
        vix_latest = round(float(vix_close[-1]), 2) if vix_close else None

        summary = (
            f"NIFTY 50 closed near {latest:.2f} with a 1-month return of {month_return:.2f}%."
            + (f" India VIX last close was {vix_latest:.2f}." if vix_latest is not None else "")
        )
        return {
            "nifty_close": round(latest, 2),
            "one_month_return_pct": month_return,
            "realized_volatility_pct": realized_vol,
            "india_vix": vix_latest,
        }, summary, "Market data is cached from Yahoo Finance and should be rechecked before high-stakes decisions."

    def _fetch_yahoo_chart(self, symbol: str, range_value: str, interval: str) -> dict:
        response = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"range": range_value, "interval": interval},
            headers={"User-Agent": self.USER_AGENT},
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        result = ((data.get("chart") or {}).get("result") or [{}])[0]
        quote = (((result.get("indicators") or {}).get("quote") or [{}])[0]) or {}
        close = [float(item) for item in quote.get("close", []) if item is not None]
        timestamps = result.get("timestamp", [])
        return {"close": close, "timestamp": timestamps}

    def _fetch_geocode(self, destination: str) -> tuple[dict, str, str]:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": destination, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": self.USER_AGENT},
            timeout=10,
        )
        response.raise_for_status()
        items = response.json()
        if not items:
            raise ValueError("No matching destination was found.")
        item = items[0]
        payload = {
            "display_name": item.get("display_name", destination),
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
        }
        summary = f"Destination resolved to {payload['display_name']}."
        return payload, summary, "OpenStreetMap geocoding is cached to avoid repeated requests and stale results are rotated out."

    def _fetch_offbeat(self, destination: str) -> tuple[dict, str, str]:
        suggestions = []
        seen = set()
        for term in ("viewpoint", "waterfall", "lake", "fort", "village", "ghat", "forest"):
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{term} near {destination}", "format": "jsonv2", "limit": 2},
                headers={"User-Agent": self.USER_AGENT},
                timeout=10,
            )
            response.raise_for_status()
            for item in response.json():
                label = item.get("display_name", "")
                if not label or label in seen:
                    continue
                seen.add(label)
                suggestions.append(
                    {
                        "title": label.split(",")[0],
                        "detail": label,
                        "latitude": float(item["lat"]),
                        "longitude": float(item["lon"]),
                    }
                )
        summary = f"Generated {len(suggestions[:6])} offbeat suggestions near {destination}."
        return {"results": suggestions[:6]}, summary, "Suggestions are cached from geocoded place results and old entries are replaced as they refresh."

    def _fetch_weather(self, latitude: float, longitude: float, start_date: date, end_date: date) -> tuple[dict, str, str]:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
                "timezone": "auto",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            timeout=10,
        )
        response.raise_for_status()
        daily = response.json().get("daily", {})
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        rainfall = daily.get("precipitation_sum", [])
        wind = daily.get("windspeed_10m_max", [])
        payload = {
            "average_max_temp": round(mean(max_temps), 1) if max_temps else None,
            "average_min_temp": round(mean(min_temps), 1) if min_temps else None,
            "precipitation_total": round(sum(rainfall), 1) if rainfall else None,
            "wind_max": round(max(wind), 1) if wind else None,
        }
        summary = (
            f"Average max temperature is {payload['average_max_temp']} C with total precipitation "
            f"{payload['precipitation_total']} mm for the selected window."
        )
        return payload, summary, "Weather is cached from Open-Meteo with short freshness windows so stale forecasts can be replaced quickly."

    def _fetch_google_news(self, feed_url: str, query: str) -> tuple[dict, str, str]:
        parsed = feedparser.parse(feed_url)
        items = []
        for entry in parsed.entries[:8]:
            source = ""
            if getattr(entry, "source", None):
                source = entry.source.get("title", "")
            items.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": source,
                }
            )
        summary = f"Loaded {len(items)} recent news items for query '{query}'."
        return {"items": items}, summary, "News feed is cached from Google News RSS and should be refreshed frequently for latest developments."

    def _fetch_remotive_jobs(self, search_term: str) -> tuple[dict, str, str]:
        response = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": search_term, "limit": 10},
            headers={"User-Agent": self.USER_AGENT},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        jobs = []
        for item in data.get("jobs", [])[:10]:
            jobs.append(
                {
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "location": item.get("candidate_required_location", ""),
                    "category": item.get("category", ""),
                    "url": item.get("url", ""),
                    "publication_date": item.get("publication_date", ""),
                    "salary": item.get("salary", ""),
                    "tags": item.get("tags", [])[:8],
                }
            )
        summary = f"Loaded {len(jobs)} remote openings for search term '{search_term}'."
        return {"jobs": jobs}, summary, "Openings are cached from the Remotive Jobs API and refreshed on a short TTL."

    def _fetch_arbeitnow_jobs(self, search_term: str) -> tuple[dict, str, str]:
        response = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"page": 1},
            headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        terms = self._job_search_terms(search_term)
        jobs = []
        for item in data.get("data", [])[:80]:
            description = self._clean_html_text(item.get("description", ""))
            tags = self._tag_list(item.get("tags", []))
            combined = " ".join(
                str(value or "")
                for value in [
                    item.get("title", ""),
                    item.get("company_name", ""),
                    item.get("location", ""),
                    description,
                    " ".join(tags),
                ]
            ).lower()
            if terms and not any(term in combined for term in terms):
                continue
            location = item.get("location") or ("Remote" if item.get("remote") else "")
            job_types = self._tag_list(item.get("job_types", []))
            jobs.append(
                {
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "location": location,
                    "category": ", ".join(job_types[:3]),
                    "url": item.get("url", ""),
                    "publication_date": self._iso_from_timestamp(item.get("created_at")),
                    "salary": self._salary_snippet(description),
                    "tags": tags[:8],
                    "description_excerpt": description[:1200],
                }
            )
            if len(jobs) >= 10:
                break
        summary = f"Loaded {len(jobs)} matching openings from Arbeitnow for search term '{search_term}'."
        return {"jobs": jobs}, summary, "Openings are cached from the Arbeitnow public job-board API and refreshed on a short TTL."

    def _fetch_remoteok_jobs(self, search_term: str) -> tuple[dict, str, str]:
        response = requests.get(
            "https://remoteok.com/api",
            headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        rows = data if isinstance(data, list) else []
        terms = self._job_search_terms(search_term)
        jobs = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            title = item.get("position") or item.get("title") or ""
            if not title:
                continue
            tags = self._tag_list(item.get("tags", []))
            description = self._clean_html_text(item.get("description", ""))
            combined = " ".join(
                str(value or "")
                for value in [
                    title,
                    item.get("company", ""),
                    item.get("location", ""),
                    " ".join(tags),
                    description,
                ]
            ).lower()
            if terms and not any(term in combined for term in terms):
                continue
            salary = item.get("salary") or self._salary_range_text(item.get("salary_min"), item.get("salary_max"), currency="USD")
            jobs.append(
                {
                    "title": title,
                    "company": item.get("company", ""),
                    "location": item.get("location") or "Remote",
                    "category": ", ".join(tags[:3]),
                    "url": item.get("url") or item.get("apply_url") or "",
                    "publication_date": str(item.get("date") or self._iso_from_timestamp(item.get("epoch")) or ""),
                    "salary": salary,
                    "tags": tags[:8],
                    "description_excerpt": description[:1200],
                }
            )
            if len(jobs) >= 10:
                break
        summary = f"Loaded {len(jobs)} matching remote openings from Remote OK for search term '{search_term}'."
        return {"jobs": jobs}, summary, "Openings are cached from the Remote OK public feed and refreshed on a short TTL."

    def _job_search_terms(self, search_term: str) -> list[str]:
        ignored = {"and", "for", "the", "with", "job", "jobs", "remote"}
        return [
            token
            for token in re.split(r"[^a-z0-9+#.]+", str(search_term or "").lower())
            if len(token) >= 3 and token not in ignored
        ][:8]

    def _clean_html_text(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", str(value or ""))
        return " ".join(text.split())

    def _tag_list(self, value) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[,|/]", value) if item.strip()]
        return []

    def _salary_snippet(self, text: str) -> str:
        for match in JOB_SALARY_SNIPPET_RE.finditer(text or ""):
            candidate = " ".join(match.group(0).split())
            if not candidate:
                continue
            lowered = candidate.lower()
            if any(token in lowered for token in ("lpa", "lakh", "crore", "cr", "inr", "rs", "usd", "$", "per", "annual", "year", "month")):
                return candidate[:80]
        return ""

    def _salary_range_text(self, minimum, maximum, *, currency: str) -> str:
        try:
            salary_min = float(minimum or 0)
            salary_max = float(maximum or 0)
        except (TypeError, ValueError):
            return ""
        if not salary_min and not salary_max:
            return ""
        if salary_min and salary_max and salary_min != salary_max:
            return f"{currency} {salary_min:.0f}-{salary_max:.0f} per year"
        value = salary_min or salary_max
        return f"{currency} {value:.0f} per year"

    def _iso_from_timestamp(self, value) -> str:
        try:
            return datetime.fromtimestamp(float(value), tz=datetime_timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return str(value or "")


verified_intelligence = VerifiedIntelligenceService()
