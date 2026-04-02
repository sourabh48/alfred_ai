from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import json
from statistics import mean
from urllib.parse import quote_plus

import feedparser
import requests
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.integrations.models import VerifiedExternalInsight


@dataclass
class InsightResult:
    payload: dict
    evidence: dict
    cached: bool


def freshness_snapshot(items: list[dict]) -> dict:
    active = [item for item in items if item]
    stale_after_values = [item.get("stale_after") for item in active if item.get("stale_after")]
    return {
        "tracked_records": len(active),
        "fresh_records": sum(1 for item in active if item.get("status") == "fresh"),
        "next_stale_after": min(stale_after_values) if stale_after_values else "",
    }


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

    def world_bank_indicator(self, indicator_code: str, title: str, stale_days: int = 30) -> InsightResult:
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
        )

    def market_snapshot(self, stale_hours: int = 12) -> InsightResult:
        return self._use_or_refresh(
            scope="market",
            cache_key="india-equity-volatility",
            title="India Market Snapshot",
            source_name="Yahoo Finance",
            source_url="https://finance.yahoo.com/quote/%5ENSEI/",
            ttl=timedelta(hours=stale_hours),
            fetcher=self._fetch_market_snapshot,
        )

    def geocode_destination(self, destination: str, stale_days: int = 30) -> InsightResult:
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
        )

    def offbeat_suggestions(self, destination: str, stale_days: int = 14) -> InsightResult:
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
        )

    def weather_snapshot(self, latitude: float, longitude: float, start_date: date, end_date: date, stale_hours: int = 8) -> InsightResult:
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
        )

    def google_news_search(self, query: str, stale_hours: int = 8) -> InsightResult:
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
        )

    def remotive_jobs(self, search_term: str, stale_hours: int = 8) -> InsightResult:
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
        )

    def tax_regime_reference(self, stale_days: int = 45) -> InsightResult:
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
        )

    def nps_tax_reference(self, stale_days: int = 45) -> InsightResult:
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
        )

    def ppf_reference(self, stale_days: int = 45) -> InsightResult:
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
    ) -> InsightResult:
        return self._use_or_refresh(
            scope=scope,
            cache_key=cache_key,
            title=title,
            source_name=source_name,
            source_url=source_url,
            ttl=ttl,
            fetcher=lambda: (payload, summary, notes),
        )

    def _use_or_refresh(self, scope: str, cache_key: str, title: str, source_name: str, source_url: str, ttl: timedelta, fetcher, query: str = "") -> InsightResult:
        self.cleanup_stale()
        record = (
            VerifiedExternalInsight.objects.filter(scope=scope, cache_key=cache_key, source_url=source_url, is_active=True)
            .order_by("-verified_at", "-id")
            .first()
        )
        if record and record.is_fresh:
            return InsightResult(record.payload, self._serialize_evidence(record), True)

        if self._circuit_is_open(scope, cache_key, source_url):
            note = self._circuit_note(scope, cache_key, source_url)
            if record:
                if record.status == "fresh":
                    record.status = "stale"
                    record.save(update_fields=["status"])
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
                    record.save(update_fields=["status"])
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
        for record in candidates:
            key = (record.scope, record.cache_key, record.source_url)
            if key in seen:
                skipped += 1
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

        return {
            "processed": processed,
            "refreshed": refreshed,
            "skipped": skipped,
            "failed": failed,
            "batch_size": batch_size,
        }

    def guardrail_snapshot(self) -> dict:
        return {
            "circuit_failure_threshold": self.CIRCUIT_FAILURE_THRESHOLD,
            "circuit_open_minutes": self.CIRCUIT_OPEN_MINUTES,
            "refresh_batch_size": self.REFRESH_BATCH_SIZE,
            "stale_lookahead_hours": self.STALE_LOOKAHEAD_HOURS,
            "fault_tolerance": [
                "Repeated upstream failures trip a circuit breaker before more external calls are attempted.",
                "If a verified record already exists, Alfred falls back to the latest stored payload instead of failing the dashboard outright.",
                "Scheduled refresh is batch-limited so one bad source cannot overload the whole refresh cycle.",
                "Stale cleanup only removes failed or inactive records after retention windows instead of deleting active evidence aggressively.",
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
            "query": query,
            "notes": notes,
        }

    def _refresh_record(self, record: VerifiedExternalInsight) -> str:
        try:
            if record.scope == "macro" and record.cache_key.startswith("world-bank:"):
                indicator = record.cache_key.split(":", 1)[1]
                self.world_bank_indicator(indicator, record.title)
                return "refreshed"
            if record.scope == "market" and record.cache_key == "india-equity-volatility":
                self.market_snapshot()
                return "refreshed"
            if record.scope == "travel" and record.cache_key.startswith("geocode:") and record.query:
                self.geocode_destination(record.query)
                return "refreshed"
            if record.scope == "travel" and record.cache_key.startswith("offbeat:") and record.query:
                self.offbeat_suggestions(record.query)
                return "refreshed"
            if record.scope == "travel" and record.cache_key.startswith("weather:"):
                _, latitude, longitude, start_date, end_date = record.cache_key.split(":")
                self.weather_snapshot(float(latitude), float(longitude), date.fromisoformat(start_date), date.fromisoformat(end_date))
                return "refreshed"
            if record.scope == "news" and record.query:
                self.google_news_search(record.query)
                return "refreshed"
            if record.scope == "jobs" and record.query:
                self.remotive_jobs(record.query)
                return "refreshed"
            if record.scope == "tax" and record.cache_key == "india-income-tax-regimes":
                self.tax_regime_reference()
                return "refreshed"
            if record.scope == "tax" and record.cache_key == "india-nps-tax-benefit":
                self.nps_tax_reference()
                return "refreshed"
            if record.scope == "tax" and record.cache_key == "india-ppf-reference":
                self.ppf_reference()
                return "refreshed"
        except Exception:
            return "failed"
        return "skipped"

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


verified_intelligence = VerifiedIntelligenceService()
