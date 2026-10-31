"""
Investment Portfolio Intelligence Service
Handles PDF imports, email scraping, portfolio analysis, and market trend suggestions.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from math import isfinite, sqrt
from statistics import mean, pstdev
from typing import Dict, List, Optional, BinaryIO
from bs4 import BeautifulSoup
from alfred_ai.services import public_http
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from alfred_ai.services import apply_parser_learning, extract_document_text
from alfred_ai.services.upload_limits import document_source
from alfred_ai.services.api_errors import safe_error_details
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import freshness_snapshot
from apps.investments.money import investment_money, investment_total_float
from apps.investments.models import Investment


AMFI_OPEN_NAV_URL = "https://portal.amfiindia.com/spages/NAVOpen.txt"
AMFI_HISTORY_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
AMFI_CACHE_TTL_SECONDS = 60 * 60 * 8
AMFI_FAILURE_CACHE_TTL_SECONDS = 60 * 15
WATCHLIST_HISTORY_DAYS = 60
WATCHLIST_TARGET_COUNT = 5
WATCHLIST_MIN_OBSERVATIONS = 18
WATCHLIST_NAV_MAX_AGE_DAYS = 7
WATCHLIST_PROOF_NEWS_LIMIT = 2
WATCHLIST_NAME_EXCLUSIONS = ("IDCW", "DIVIDEND", "BONUS", "UNCLAIMED", "SEGREGATED", "REGULAR", "INTERVAL")
WATCHLIST_NAME_REQUIRED = ("DIRECT", "GROWTH")
WATCHLIST_FAMILY_MAP = {
    "Large Cap Fund": "equity_core",
    "Flexi Cap Fund": "equity_core",
    "Index Funds": "equity_core",
    "Large & Mid Cap Fund": "equity_core",
    "Value Fund": "equity_core",
    "Contra Fund": "equity_core",
    "Focused Fund": "equity_core",
    "Multi Cap Fund": "equity_satellite",
    "Mid Cap Fund": "equity_satellite",
    "Small Cap Fund": "equity_satellite",
    "Aggressive Hybrid Fund": "hybrid",
    "Balanced Advantage Fund": "hybrid",
    "Multi Asset Allocation": "hybrid",
    "Dynamic Asset Allocation": "hybrid",
    "Gold ETF": "gold",
    "Gold Fund": "gold",
    "Short Duration Fund": "debt",
    "Corporate Bond Fund": "debt",
    "Banking and PSU Fund": "debt",
    "Money Market": "debt",
    "Liquid Fund": "debt",
    "Arbitrage Fund": "debt",
}
WATCHLIST_FAMILY_LABELS = {
    "equity_core": "Core equity",
    "equity_satellite": "Higher-beta equity",
    "hybrid": "Balanced allocation",
    "gold": "Gold hedge",
    "debt": "Defensive debt",
}
WATCHLIST_NEWS_QUERY = {
    "equity_core": "India equity mutual fund inflows",
    "equity_satellite": "India midcap mutual fund flows",
    "hybrid": "India balanced advantage fund flows",
    "gold": "India gold ETF inflows",
    "debt": "India debt mutual fund yields",
}


def _load_yfinance():
    try:
        import yfinance as yf  # pylint: disable=import-outside-toplevel
        return yf
    except Exception:
        return None


class PortfolioIntelligenceService:
    """ML-powered investment portfolio management and analysis."""

    def parse_portfolio_pdf(self, pdf_file: BinaryIO, user, *, filename: str = "") -> Dict[str, any]:
        """
        Parse investment portfolio from PDF (broker statements, mutual fund statements).
        Supports multiple formats from Groww, Zerodha, etc.
        """
        parsed = self.parse_portfolio_document(pdf_file, user=user, filename=filename)
        investments_created = []
        investments_updated = []
        if parsed.get("parser_status") == "failed":
            return {
                "success": False,
                "error": parsed.get("parser_notes") or "Portfolio document could not be parsed.",
                "created": 0,
                "updated": 0,
                "parser_status": parsed.get("parser_status"),
                "confidence": parsed.get("confidence", 0),
                "broker": parsed.get("broker", ""),
                "summary": parsed.get("summary", ""),
                "extracted_text": parsed.get("extracted_text", ""),
                "payload": parsed.get("payload", {}),
            }

        with transaction.atomic():
            for inv_data in parsed.get("investments", []):
                investment, created = self._create_or_update_investment(user, inv_data)
                if created:
                    investments_created.append(investment)
                else:
                    investments_updated.append(investment)

        return {
            "success": True,
            "created": len(investments_created),
            "updated": len(investments_updated),
            "investments": investments_created + investments_updated,
            "parser_status": parsed.get("parser_status"),
            "confidence": parsed.get("confidence", 0),
            "broker": parsed.get("broker", ""),
            "summary": parsed.get("summary", ""),
            "extracted_text": parsed.get("extracted_text", ""),
            "payload": parsed.get("payload", {}),
        }

    def parse_portfolio_document(self, pdf_file: BinaryIO, *, user, filename: str = "") -> Dict[str, any]:
        raw_bytes = document_source(pdf_file)
        extracted = extract_document_text(raw_bytes, filename or getattr(pdf_file, "name", "portfolio.pdf"), ocr_page_limit=8)
        full_text = extracted.text or ""
        broker = self._detect_broker(full_text)

        parsed_investments, layout_review = self._parse_holdings_table(full_text, broker=broker)
        # OCR diagnostics can be present even when digital text won; use the selected method.
        if any(token in extracted.method.lower() for token in ("ocr", "tesseract")):
            parsed_investments = []
            layout_review = {"status": "needs_review", "reason": "OCR table amounts and account identity require source review before import."}
        if layout_review and len(full_text) >= 30000:
            parsed_investments = []
            layout_review = {"status": "needs_review", "reason": "Extraction reached its text bound; review the complete source before import."}
        if layout_review is None:
            if "ZERODHA" in broker.upper():
                parsed_investments = self._parse_zerodha_statement(full_text)
            elif "GROWW" in broker.upper():
                parsed_investments = self._parse_groww_statement(full_text)
            else:
                parsed_investments = self._parse_generic_statement(full_text, broker=broker)

        account_number = self._extract_account_hint(full_text)
        if layout_review is not None:
            accounts = {item["account_number"] for item in parsed_investments}
            account_number = next(iter(accounts)) if len(accounts) == 1 else ""
        field_names = sorted(
            {
                *[key for item in parsed_investments for key, value in item.items() if value not in ("", None, 0)],
                *([ "broker_name" ] if broker and broker != "Generic" else []),
                *([ "account_number" ] if account_number else []),
            }
        )
        base_confidence = min(0.94, max(0.08, extracted.confidence + (0.12 if parsed_investments else -0.08)))
        confidence, learning_notes = apply_parser_learning(
            user=user,
            scope="investment_document",
            filename=filename or getattr(pdf_file, "name", "portfolio.pdf"),
            detected_type=(broker or "portfolio_statement").lower().replace(" ", "_"),
            text=full_text,
            field_names=field_names,
            confidence=base_confidence,
        )
        if parsed_investments:
            parser_status = "parsed"
        elif full_text.strip() or confidence >= 0.22 or broker != "Generic":
            parser_status = "needs_review"
        else:
            parser_status = "failed"

        notes = [*extracted.notes, *learning_notes]
        if layout_review:
            notes.append(layout_review["reason"])
        summary = (
            f"{len(parsed_investments)} investment position(s) were extracted from the {broker} document."
            if parsed_investments
            else f"The {broker if broker != 'Generic' else 'portfolio'} document was saved, but Alfred could not extract enough structured holdings yet."
        )
        return {
            "broker": broker,
            "confidence": confidence,
            "parser_status": parser_status,
            "parser_notes": " ".join(note for note in notes if note).strip(),
            "extracted_text": full_text,
            "summary": summary,
            "investments": parsed_investments,
            "payload": {
                "broker_name": broker,
                "account_number": account_number,
                "extraction_method": extracted.method,
                "raw_notes": notes[:8],
                "raw_text_excerpt": " ".join(full_text.split())[:600],
                "extraction_review": extracted.review_payload,
                "layout_review": layout_review,
                "investments": parsed_investments,
            },
        }

    def scrape_email_for_investments(self, user, email_config: Dict) -> Dict[str, any]:
        """
        Scrape user's email for investment-related communications.
        Looks for broker statements, mutual fund updates, etc.
        """
        from apps.integrations.services.email_integration import EmailIntegrationService

        email_integration_service = EmailIntegrationService()

        email_config = email_config or {}
        try:
            days_back = max(1, min(int(email_config.get("days_back") or 30), 365))
        except (TypeError, ValueError):
            days_back = 30
        connected_here = False
        if email_config.get("imap_server") and email_config.get("email_address") and email_config.get("password"):
            connection = email_integration_service.connect_imap(
                email_address=email_config["email_address"],
                password=email_config["password"],
                imap_server=email_config["imap_server"],
                port=int(email_config.get("port") or 993),
            )
            if not connection.get("success"):
                error = connection.get("error", "Email connection failed.")
                return {
                    "success": False,
                    "message": error,
                    "imported": 0,
                    "updated": 0,
                    "scanned": 0,
                    "parsed_files": [],
                    "errors": [error],
                }
            connected_here = True

        try:
            scan = email_integration_service.scan_financial_emails(user, days_back=days_back)
            if scan.get("error"):
                return {
                    "success": False,
                    "message": scan["error"],
                    "imported": 0,
                    "updated": 0,
                    "scanned": 0,
                    "parsed_files": [],
                    "errors": [scan["error"]],
                }

            investment_messages = [
                *scan.get("investment_statements", []),
                *scan.get("mutual_fund_statements", []),
            ]
            imported = 0
            updated = 0
            errors = []
            parsed_files = []
            supported_extensions = {".pdf", ".txt", ".csv"}

            for message in investment_messages:
                attachments = list(message.get("attachments") or [])
                for index, attachment in enumerate(attachments):
                    filename = attachment.get("filename") or f"investment-attachment-{index + 1}.pdf"
                    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                    if extension and extension not in supported_extensions:
                        continue

                    file_obj = None
                    if attachment.get("data"):
                        from io import BytesIO

                        file_obj = BytesIO(attachment["data"])
                        file_obj.name = filename
                    elif message.get("id"):
                        file_obj = email_integration_service.download_statement(message["id"], index)

                    if file_obj is None:
                        errors.append(f"{filename}: attachment could not be downloaded")
                        continue

                    result = self.parse_portfolio_pdf(file_obj, user=user, filename=filename)
                    imported += int(result.get("created") or 0)
                    updated += int(result.get("updated") or 0)
                    parsed_files.append(
                        {
                            "filename": filename,
                            "parser_status": result.get("parser_status", ""),
                            "confidence": result.get("confidence", 0),
                            "created": result.get("created", 0),
                            "updated": result.get("updated", 0),
                        }
                    )
                    if not result.get("success"):
                        errors.append(f"{filename}: {result.get('error', 'parse failed')}")

            return {
                "success": not errors,
                "message": (
                    f"Scanned {len(investment_messages)} investment email(s); imported {imported} and updated {updated} holding(s)."
                    if investment_messages
                    else "No investment statement emails were found in the selected window."
                ),
                "scanned": len(investment_messages),
                "imported": imported,
                "updated": updated,
                "parsed_files": parsed_files,
                "errors": errors,
            }
        finally:
            if connected_here:
                email_integration_service.disconnect()

    def analyze_portfolio_risk(self, user) -> Dict[str, any]:
        """Analyze portfolio risk profile and diversification."""
        investments = list(Investment.objects.filter(user=user))

        if not investments:
            return {
                "risk_score": 0,
                "risk_level": "UNKNOWN",
                "diversification_score": 0,
                "recommendations": ["No investments found. Start investing to build wealth."],
            }

        total_value = sum(item.current_value for item in investments)

        # Calculate asset allocation
        asset_breakdown = {}
        for asset_type, label in Investment.ASSET_TYPES:
            type_value = sum(item.current_value for item in investments if item.asset_type == asset_type)
            if type_value > 0:
                asset_breakdown[label] = {
                    "value": investment_total_float(type_value),
                    "percentage": float(round((type_value / total_value * 100), 2)),
                }

        # Risk scoring (0-100)
        risk_score = self._calculate_portfolio_risk_score(asset_breakdown, total_value)

        # Diversification score (0-100)
        diversification_score = self._calculate_diversification_score(asset_breakdown)

        # Generate recommendations
        recommendations = self._generate_portfolio_recommendations(
            asset_breakdown, risk_score, diversification_score
        )

        risk_level = self._get_risk_level(risk_score)

        return {
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "diversification_score": round(diversification_score, 2),
            "total_portfolio_value": investment_total_float(total_value),
            "asset_allocation": asset_breakdown,
            "recommendations": recommendations,
        }

    def get_market_trends_and_suggestions(self, user) -> Dict[str, any]:
        """
        Build source-backed market context and portfolio suggestions.
        """
        suggestions = []
        evidence = []
        market = verified_intelligence.market_snapshot()
        inflation = verified_intelligence.world_bank_indicator("FP.CPI.TOTL.ZG", "India inflation rate")
        evidence.extend([market.evidence, inflation.evidence])

        market_values = self._market_values(market.payload)
        try:
            raw_inflation = inflation.payload.get("latest_value")
            inflation_value = float(raw_inflation) if not isinstance(raw_inflation, bool) else float("nan")
        except (TypeError, ValueError, OverflowError):
            inflation_value = float("nan")
        if not freshness_snapshot(evidence)["proof_complete"] or market_values is None or not isfinite(inflation_value):
            return {
                "suggestions": [{"type": "source_unavailable", "message": "Market guidance is unavailable: required source observations are missing, invalid or expired."}],
                "evidence": evidence, "freshness": freshness_snapshot(evidence),
                "last_updated": timezone.now().isoformat(),
            }
        market_return, vix = market_values

        market_trend = "bullish" if market_return >= 0 else "defensive"
        suggestions.append({
            "type": "market_overview",
            "message": (
                f"Verified market context is {market_trend}: NIFTY 1-month return {market_return:.2f}%"
                + (f", India VIX {vix:.2f}." if vix else ".")
            ),
        })
        if inflation_value:
            suggestions.append({
                "type": "macro_context",
                "message": f"Latest tracked inflation reference is {inflation_value:.2f}%, which matters for real-return planning and debt-vs-equity balance.",
            })

        # Analyze user's portfolio and suggest actions
        user_investments = list(Investment.objects.filter(user=user))

        # Suggest rebalancing if needed
        if user_investments:
            total_value = sum(item.current_value for item in user_investments)
            equity_percentage = sum(item.current_value for item in user_investments if item.asset_type == "equity") / total_value * 100 if total_value > 0 else 0

            if equity_percentage > 70:
                suggestions.append({
                    "type": "rebalancing",
                    "message": f"Your portfolio has {equity_percentage:.1f}% equity exposure. "
                              "Consider diversifying into debt or gold for better risk management.",
                })
            elif equity_percentage < 25 and total_value > 0:
                suggestions.append({
                    "type": "rebalancing",
                    "message": f"Equity exposure is only {equity_percentage:.1f}%. If your horizon is long, you may be under-exposed to growth assets.",
                })

        if vix and vix >= 18:
            suggestions.append({
                "type": "volatility",
                "message": "Volatility is elevated. Fresh SIPs may be safer than large lump-sum deployment if your cash buffer is limited.",
            })

        # AI-generated suggestions based on user profile
        user_age = getattr(user, "age", 30)
        if user_age < 35:
            suggestions.append({
                "type": "age_based",
                "message": "As a young investor, consider aggressive equity/SIP investments for long-term wealth creation.",
            })
        elif user_age > 50:
            suggestions.append({
                "type": "age_based",
                "message": "Consider increasing debt allocation for stability as you approach retirement.",
            })

        return {
            "suggestions": suggestions,
            "evidence": evidence,
            "freshness": freshness_snapshot(evidence),
            "last_updated": timezone.now().isoformat(),
        }

    def build_short_horizon_watchlist(self, user) -> Dict[str, any]:
        """
        Build a transparent 1-2 month watchlist from official AMFI NAV data plus
        verified market/news context. This is a watchlist, not a guarantee.
        """
        market = verified_intelligence.market_snapshot()
        latest_nav_report = self._get_amfi_latest_nav_report()
        history_report = (
            self._get_amfi_history_report(days=WATCHLIST_HISTORY_DAYS)
            if latest_nav_report["items"]
            else self._empty_amfi_history_report(
                days=WATCHLIST_HISTORY_DAYS,
                summary="Skipped AMFI history fetch because the latest NAV report is unavailable.",
            )
        )

        evidence = [market.evidence, latest_nav_report["evidence"], history_report["evidence"]]
        market_values = self._market_values(market.payload)
        if not latest_nav_report["items"] or not history_report["series"] or market_values is None or not freshness_snapshot(evidence)["proof_complete"]:
            return {
                "available": False,
                "summary": "Watchlist unavailable: required market or AMFI observations are missing, invalid or expired. Recorded holdings are unchanged.",
                "algorithm": self._watchlist_algorithm_payload(),
                "items": [],
                "evidence": evidence,
                "freshness": self._evidence_freshness(evidence),
                "generated_at": timezone.now().isoformat(),
            }

        portfolio_mix = self._portfolio_mix(user)
        regime = self._market_regime(
            market_return=market_values[0],
            vix=market_values[1],
        )
        ranked = self._rank_watchlist_candidates(
            latest_items=latest_nav_report["items"],
            history_series=history_report["series"],
            market=market.payload,
            regime=regime,
            portfolio_mix=portfolio_mix,
        )
        selected = self._select_watchlist_items(ranked)
        news_payloads = self._watchlist_news_payloads(selected)
        evidence.extend([item["evidence"] for item in news_payloads.values() if item.get("evidence")])
        items = [
            self._serialize_watchlist_item(item, regime=regime, market=market.payload, news_payloads=news_payloads)
            for item in selected
        ]
        summary = (
            f"Built a {regime['label'].replace('_', ' ')} 1-2 month watchlist from official AMFI NAV history, "
            "current market regime, and user portfolio fit. These are ranked watch candidates, not guaranteed gain calls."
        )
        if not items:
            summary = "Watchlist unavailable: no funds have recent, consistent source identities and sufficient distinct historical observations. Recorded holdings are unchanged."
        return {
            "available": bool(items),
            "summary": summary,
            "algorithm": self._watchlist_algorithm_payload(),
            "regime": regime,
            "items": items,
            "evidence": evidence,
            "freshness": self._evidence_freshness(evidence),
            "generated_at": timezone.now().isoformat(),
            "portfolio_fit": portfolio_mix,
        }

    def _detect_broker(self, text: str) -> str:
        """Detect broker from statement text."""
        text_upper = text.upper()
        if "ZERODHA" in text_upper:
            return "Zerodha"
        elif "GROWW" in text_upper:
            return "Groww"
        elif "UPSTOX" in text_upper:
            return "Upstox"
        elif "ANGLE ONE" in text_upper or "ANGEL BROKING" in text_upper:
            return "Angel One"
        return "Generic"

    def _get_amfi_latest_nav_report(self) -> dict:
        cache_key = "investments:amfi:latest-open-nav:v2"
        cached = cache.get(cache_key)
        if cached:
            return cached
        fetched_at = timezone.now()
        try:
            response = public_http.request("GET", AMFI_OPEN_NAV_URL,
                content_types=("text/plain",), max_bytes=8_000_000)
            text = response.content.decode("utf-8-sig", errors="replace")
            items = self._parse_amfi_nav_report(text, history_mode=False)
        except Exception as exc:
            safe_error_details(exc, "AMFI latest NAV report could not be loaded.", logger_name=__name__)
            report = {
                "items": [],
                "evidence": self._external_evidence(
                    source_name="AMFI",
                    source_url=AMFI_OPEN_NAV_URL,
                    summary="AMFI latest NAV report could not be loaded.",
                    fetched_at=fetched_at,
                    ttl_seconds=AMFI_FAILURE_CACHE_TTL_SECONDS,
                    notes="Official AMFI latest NAV fetch failed; short-horizon watchlist degrades to unavailable instead of failing the portfolio dashboard.",
                    status="failed",
                ),
            }
            cache.set(cache_key, report, AMFI_FAILURE_CACHE_TTL_SECONDS)
            return report
        report = {
            "items": items,
            "evidence": self._external_evidence(
                source_name="AMFI",
                source_url=AMFI_OPEN_NAV_URL,
                summary=f"Loaded {len(items)} open-ended fund NAV rows from the latest official AMFI text report.",
                fetched_at=fetched_at,
                ttl_seconds=AMFI_CACHE_TTL_SECONDS,
                notes="Official AMFI latest NAV text report; filtered later to direct-growth shortlist candidates.",
                status="fresh" if items else "failed",
            ),
        }
        cache.set(cache_key, report, AMFI_CACHE_TTL_SECONDS)
        return report

    def _get_amfi_history_report(self, *, days: int) -> dict:
        to_date = timezone.localdate()
        from_date = to_date - timedelta(days=days)
        cache_key = f"investments:amfi:history:{from_date.isoformat()}:{to_date.isoformat()}:v2"
        cached = cache.get(cache_key)
        if cached:
            return cached
        fetched_at = timezone.now()
        source_url = f"{AMFI_HISTORY_URL}?frmdt={from_date.strftime('%d-%b-%Y')}&todt={to_date.strftime('%d-%b-%Y')}"
        try:
            response = public_http.request("GET",
                AMFI_HISTORY_URL,
                params={
                    "frmdt": from_date.strftime("%d-%b-%Y"),
                    "todt": to_date.strftime("%d-%b-%Y"),
                },
                content_types=("text/plain", "text/html"), max_bytes=16_000_000,
            )
            text = response.content.decode("utf-8-sig", errors="replace")
            series = self._parse_amfi_nav_report(text, history_mode=True)
        except Exception as exc:
            safe_error_details(exc, "AMFI NAV history could not be loaded.", logger_name=__name__)
            report = {
                "series": [],
                "evidence": self._external_evidence(
                    source_name="AMFI",
                    source_url=source_url,
                    summary="AMFI NAV history could not be loaded.",
                    fetched_at=fetched_at,
                    ttl_seconds=AMFI_FAILURE_CACHE_TTL_SECONDS,
                    notes="Official AMFI history fetch failed; short-horizon watchlist degrades to unavailable instead of failing the portfolio dashboard.",
                    status="failed",
                ),
            }
            cache.set(cache_key, report, AMFI_FAILURE_CACHE_TTL_SECONDS)
            return report
        report = {
            "series": series,
            "evidence": self._external_evidence(
                source_name="AMFI",
                source_url=source_url,
                summary=f"Loaded official AMFI NAV history from {from_date.isoformat()} to {to_date.isoformat()} for short-horizon scoring.",
                fetched_at=fetched_at,
                ttl_seconds=AMFI_CACHE_TTL_SECONDS,
                notes="Official AMFI history endpoint; Alfred uses the latest 60-day NAV window for momentum, drawdown, and volatility math.",
                status="fresh" if series else "failed",
            ),
        }
        cache.set(cache_key, report, AMFI_CACHE_TTL_SECONDS)
        return report

    def _empty_amfi_history_report(self, *, days: int, summary: str) -> dict:
        to_date = timezone.localdate()
        from_date = to_date - timedelta(days=days)
        fetched_at = timezone.now()
        return {
            "series": [],
            "evidence": self._external_evidence(
                source_name="AMFI",
                source_url=f"{AMFI_HISTORY_URL}?frmdt={from_date.strftime('%d-%b-%Y')}&todt={to_date.strftime('%d-%b-%Y')}",
                summary=summary,
                fetched_at=fetched_at,
                ttl_seconds=AMFI_FAILURE_CACHE_TTL_SECONDS,
                notes="History fetch was skipped after an earlier AMFI dependency failed.",
                status="failed",
            ),
        }

    def _parse_amfi_nav_report(self, text: str, *, history_mode: bool) -> list[dict]:
        current_category = ""
        current_house = ""
        rows: list[dict] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("Scheme Code;"):
                continue
            if ";" not in line:
                if "Open Ended Schemes" in line or "Close Ended Schemes" in line:
                    current_category = line
                elif len(line) > 3:
                    current_house = line
                continue
            parts = [part.strip() for part in line.split(";")]
            if not parts or not parts[0].isdigit():
                continue
            if history_mode:
                if len(parts) < 8:
                    continue
                scheme_name = parts[1]
                nav_value = self._parse_nav(parts[4])
                nav_date = self._parse_amfi_date(parts[7])
            else:
                if len(parts) < 6:
                    continue
                scheme_name = parts[3]
                nav_value = self._parse_nav(parts[4])
                nav_date = self._parse_amfi_date(parts[5])
            if nav_value is None or nav_date is None or nav_date > timezone.localdate():
                continue
            rows.append(
                {
                    "scheme_code": parts[0],
                    "scheme_name": scheme_name,
                    "fund_house": current_house,
                    "category": current_category,
                    "nav": nav_value,
                    "nav_date": nav_date,
                    "isin_growth": parts[2] if history_mode else parts[1],
                    "isin_reinvestment": parts[3] if history_mode else parts[2],
                }
            )
        return rows

    def _rank_watchlist_candidates(self, *, latest_items: list[dict], history_series: list[dict], market: dict, regime: dict, portfolio_mix: dict) -> list[dict]:
        latest_by_code = {}
        conflicting = set()
        today = timezone.localdate()
        for item in latest_items:
            if not self._is_watchlist_candidate(item) or not 0 <= (today - item["nav_date"]).days <= WATCHLIST_NAV_MAX_AGE_DAYS:
                continue
            code = item["scheme_code"]
            if code in latest_by_code and latest_by_code[code] != item:
                conflicting.add(code)
            latest_by_code[code] = item
        for code in conflicting:
            latest_by_code.pop(code, None)
        history_by_code: dict[str, list[dict]] = defaultdict(list)
        for row in history_series:
            if row["scheme_code"] not in latest_by_code:
                continue
            history_by_code[row["scheme_code"]].append(row)

        ranked: list[dict] = []
        for scheme_code, latest in latest_by_code.items():
            series = sorted(history_by_code.get(scheme_code, []), key=lambda item: item["nav_date"])
            identity = ("scheme_name", "isin_growth", "isin_reinvestment")
            if any(any(str(row.get(field, "")).casefold() != str(latest.get(field, "")).casefold() for field in identity)
                   or not latest["nav_date"] - timedelta(days=WATCHLIST_HISTORY_DAYS) <= row["nav_date"] <= latest["nav_date"] for row in series):
                continue
            metrics = self._series_metrics(series)
            if metrics is None or metrics["observation_count"] < WATCHLIST_MIN_OBSERVATIONS:
                continue
            if metrics["return_10d_pct"] is None or metrics["return_30d_pct"] is None:
                continue
            if series[-1]["nav_date"] != latest["nav_date"] or series[-1]["nav"] != latest["nav"]:
                continue
            family = self._watchlist_family(latest["category"], latest["scheme_name"])
            if not family:
                continue
            regime_fit = self._regime_fit_score(family, regime["label"])
            diversification_fit = self._diversification_fit_score(family, portfolio_mix)
            score = (
                48
                + (metrics["return_30d_pct"] * 2.6)
                + (metrics["return_10d_pct"] * 1.6)
                + (metrics["max_drawdown_pct"] * 1.15)
                - (metrics["realized_volatility_pct"] * 2.2)
                + regime_fit
                + diversification_fit
            )
            ranked.append(
                {
                    **latest,
                    **metrics,
                    "family": family,
                    "family_label": WATCHLIST_FAMILY_LABELS.get(family, family.replace("_", " ").title()),
                    "market_return_pct": float(market.get("one_month_return_pct") or 0),
                    "india_vix": float(market.get("india_vix") or 0),
                    "regime_fit_score": regime_fit,
                    "diversification_fit_score": diversification_fit,
                    "short_horizon_score": round(max(0.0, min(score, 100.0)), 1),
                }
            )
        ranked.sort(
            key=lambda item: (
                float(item["short_horizon_score"]),
                float(item["return_30d_pct"]),
                float(item["return_10d_pct"]),
            ),
            reverse=True,
        )
        return ranked

    def _select_watchlist_items(self, ranked: list[dict]) -> list[dict]:
        selected: list[dict] = []
        used_ids: set[str] = set()
        used_families: set[str] = set()
        used_houses: set[str] = set()

        for item in ranked:
            if len(selected) >= WATCHLIST_TARGET_COUNT:
                break
            if item["family"] in used_families:
                continue
            if item["fund_house"] and item["fund_house"] in used_houses:
                continue
            selected.append(item)
            used_ids.add(item["scheme_code"])
            used_families.add(item["family"])
            if item["fund_house"]:
                used_houses.add(item["fund_house"])

        for item in ranked:
            if len(selected) >= WATCHLIST_TARGET_COUNT:
                break
            if item["scheme_code"] in used_ids:
                continue
            if item["fund_house"] and item["fund_house"] in used_houses:
                continue
            selected.append(item)
            used_ids.add(item["scheme_code"])
            if item["fund_house"]:
                used_houses.add(item["fund_house"])

        return selected[:WATCHLIST_TARGET_COUNT]

    def _serialize_watchlist_item(self, item: dict, *, regime: dict, market: dict, news_payloads: dict) -> dict:
        outlook_label = self._watchlist_outlook_label(item["short_horizon_score"])
        why = [
            f"30-day NAV trend is {item['return_30d_pct']:.2f}%.",
            f"10-day confirmation trend is {item['return_10d_pct']:.2f}%.",
            f"Largest observed peak-to-trough decline over {item['history_days']} days is {abs(item['max_drawdown_pct']):.2f}%.",
            f"Observation-return volatility (21-observation scale) is {item['realized_volatility_pct']:.2f}%; gaps are not a daily forecast.",
            f"{item['family_label']} currently fits the {regime['label'].replace('_', ' ')} market regime.",
        ]
        proof = [
            {
                "label": "AMFI latest NAV",
                "source_url": AMFI_OPEN_NAV_URL,
                "summary": f"Official AMFI latest NAV is {item['nav']:.4f} as of {item['nav_date'].isoformat()}.",
            },
            {
                "label": "AMFI NAV history",
                "source_url": self._history_proof_url(),
                "summary": (
                    f"Official AMFI history shows 30-day return {item['return_30d_pct']:.2f}%, "
                    f"10-day return {item['return_10d_pct']:.2f}%, and observed-window drawdown {item['max_drawdown_pct']:.2f}%. "
                    f"Observed {item['history_start']} to {item['history_end']}; lookbacks use the latest prior observation."
                ),
            },
        ]
        news_payload = news_payloads.get(item["family"], {})
        news_items = (news_payload.get("payload") or {}).get("items", [])[:WATCHLIST_PROOF_NEWS_LIMIT]
        if news_items:
            proof.append(
                {
                    "label": news_payload["evidence"]["source_name"],
                    "source_url": news_payload["evidence"]["source_url"],
                    "summary": news_items[0].get("title", ""),
                }
            )
        proof.append(
            {
                "label": "Market regime proof",
                "source_url": market.get("source_url", "") or "https://finance.yahoo.com/quote/%5ENSEI/",
                "summary": (
                    f"NIFTY 1-month return is {float(market.get('one_month_return_pct') or 0):.2f}% "
                    f"and India VIX is {float(market.get('india_vix') or 0):.2f}."
                ),
            }
        )
        return {
            "scheme_code": item["scheme_code"],
            "scheme_name": item["scheme_name"],
            "fund_house": item["fund_house"],
            "category": item["category"],
            "family": item["family"],
            "family_label": item["family_label"],
            "nav": float(round(item["nav"], 4)),
            "nav_source_value": str(item["nav"]),
            "nav_date": item["nav_date"].isoformat(),
            "observation_count": item["observation_count"],
            "history_days": item["history_days"],
            "history_start": item["history_start"],
            "history_end": item["history_end"],
            "return_baselines": item["return_baselines"],
            "short_horizon_score": item["short_horizon_score"],
            "outlook_label": outlook_label,
            "return_10d_pct": round(item["return_10d_pct"], 2),
            "return_30d_pct": round(item["return_30d_pct"], 2),
            "return_60d_pct": round(item["return_60d_pct"], 2) if item["return_60d_pct"] is not None else None,
            "max_drawdown_pct": round(item["max_drawdown_pct"], 2),
            "realized_volatility_pct": round(item["realized_volatility_pct"], 2),
            "why_it_ranked": why[:5],
            "proof": proof,
            "caution": "This is a transparent watchlist score for the next 1-2 months, not a guaranteed return signal or a substitute for suitability advice.",
        }

    def _series_metrics(self, series: list[dict]) -> dict | None:
        observations = {}
        for row in series:
            day = row.get("nav_date")
            nav = self._parse_nav(row.get("nav"))
            if type(day) is not date or nav is None or (day in observations and observations[day] != nav):
                return None
            observations[day] = nav
        dates = sorted(observations)
        if len(dates) < 2:
            return None
        navs = [observations[day] for day in dates]
        baselines = {days: next((day for day in reversed(dates) if day <= dates[-1] - timedelta(days=days)), None)
                     for days in (10, 30, 60)}
        for days, day in baselines.items():
            if day is not None and (dates[-1] - day).days - days > WATCHLIST_NAV_MAX_AGE_DAYS:
                baselines[days] = None
        with localcontext() as context:
            context.prec = 28
            returns = {f"return_{days}d_pct": float((navs[-1] / observations[day] - 1) * 100) if day else None
                       for days, day in baselines.items()}
            changes = [float(current / previous - 1) for previous, current in zip(navs, navs[1:])]
            if not all(isfinite(value) for value in changes + [v for v in returns.values() if v is not None]):
                return None
            peak, drawdown = navs[0], Decimal(0)
            for nav in navs:
                peak = max(peak, nav)
                drawdown = min(drawdown, (nav / peak - 1) * 100)
        try:
            volatility = pstdev(changes) * sqrt(21) * 100 if len(changes) >= 2 else 0.0
        except (OverflowError, ValueError):
            return None
        if not isfinite(volatility):
            return None
        return {**returns, "max_drawdown_pct": float(drawdown), "realized_volatility_pct": volatility,
                "observation_count": len(dates), "history_days": (dates[-1] - dates[0]).days,
                "history_start": dates[0].isoformat(), "history_end": dates[-1].isoformat(),
                "return_baselines": {str(days): day.isoformat() if day else None for days, day in baselines.items()}}

    def _portfolio_mix(self, user) -> dict:
        investments = list(Investment.objects.filter(user=user).only("asset_type", "current_value"))
        total_value = sum(item.current_value for item in investments)
        if not total_value:
            return {"equity_pct": 0.0, "debt_pct": 0.0, "gold_pct": 0.0, "hybrid_pct": 0.0}
        equity_types = {"equity", "mutual_fund", "reit", "crypto"}
        debt_types = {"debt", "cash"}
        gold_types = {"gold"}
        return {
            "equity_pct": float(round(sum(item.current_value for item in investments if item.asset_type in equity_types) / total_value * 100, 2)),
            "debt_pct": float(round(sum(item.current_value for item in investments if item.asset_type in debt_types) / total_value * 100, 2)),
            "gold_pct": float(round(sum(item.current_value for item in investments if item.asset_type in gold_types) / total_value * 100, 2)),
            "hybrid_pct": float(round(sum(item.current_value for item in investments if item.asset_type == "mutual_fund") / total_value * 100, 2)),
        }

    def _market_regime(self, *, market_return: float, vix: float) -> dict:
        if market_return >= 1.5 and (not vix or vix < 16):
            return {
                "label": "constructive_equity",
                "summary": "Broad market trend is constructive and volatility is contained, so diversified equity funds get a stronger regime fit.",
            }
        if market_return < -1 or (vix and vix >= 18):
            return {
                "label": "defensive_rotation",
                "summary": "Near-term market stress is elevated, so gold, debt, and balanced funds get a stronger regime fit than high-beta equity funds.",
            }
        return {
            "label": "balanced_watch",
            "summary": "Momentum is mixed, so Alfred prefers balanced, large-cap, and diversified funds over narrow high-beta bets.",
        }

    def _regime_fit_score(self, family: str, regime_label: str) -> float:
        matrix = {
            "constructive_equity": {"equity_core": 14, "equity_satellite": 9, "hybrid": 6, "gold": 0, "debt": -2},
            "balanced_watch": {"equity_core": 8, "equity_satellite": 3, "hybrid": 10, "gold": 4, "debt": 5},
            "defensive_rotation": {"equity_core": 2, "equity_satellite": -6, "hybrid": 8, "gold": 12, "debt": 10},
        }
        return float(matrix.get(regime_label, {}).get(family, 0))

    def _diversification_fit_score(self, family: str, portfolio_mix: dict) -> float:
        equity_pct = float(portfolio_mix.get("equity_pct", 0) or 0)
        debt_pct = float(portfolio_mix.get("debt_pct", 0) or 0)
        gold_pct = float(portfolio_mix.get("gold_pct", 0) or 0)
        if family in {"equity_core", "equity_satellite"}:
            if equity_pct >= 70:
                return -6.0
            if equity_pct <= 35:
                return 4.0
            return 0.0
        if family == "gold":
            return 5.0 if gold_pct < 8 else 1.0
        if family == "debt":
            return 5.0 if debt_pct < 20 else 1.0
        if family == "hybrid":
            return 4.0 if equity_pct >= 65 or debt_pct <= 15 else 2.0
        return 0.0

    def _watchlist_news_payloads(self, selected: list[dict]) -> dict:
        payloads = {}
        for family in {item["family"] for item in selected}:
            query = WATCHLIST_NEWS_QUERY.get(family)
            if not query:
                continue
            try:
                insight = verified_intelligence.google_news_search(query, stale_hours=8)
            except Exception:
                continue
            payloads[family] = {"payload": insight.payload, "evidence": insight.evidence}
        return payloads

    def _watchlist_algorithm_payload(self) -> dict:
        return {
            "name": "Transparent short-horizon fund watchlist",
            "window_days": WATCHLIST_HISTORY_DAYS,
            "factors": [
                {"label": "30-day NAV momentum", "effect": "positive"},
                {"label": "10-day confirmation momentum", "effect": "positive"},
                {"label": "Observed-window peak-to-trough drawdown", "effect": "negative"},
                {"label": "Realized volatility", "effect": "negative"},
                {"label": "Current market regime fit", "effect": "positive"},
                {"label": "User portfolio diversification fit", "effect": "positive"},
            ],
            "guardrail": "Research only: NAV dates and prior lookback observations must be within 7 calendar days of their target date, with distinct consistent observations. Missing 60-day coverage stays unavailable; no currency conversion or holding revaluation. No guaranteed returns.",
        }

    def _watchlist_family(self, category: str, scheme_name: str) -> str:
        category_upper = category.upper()
        scheme_upper = scheme_name.upper()
        if "GOLD ETF" in scheme_upper or "GOLD FUND" in scheme_upper:
            return "gold"
        for keyword, family in WATCHLIST_FAMILY_MAP.items():
            if keyword.upper() in category_upper:
                return family
        return ""

    def _watchlist_outlook_label(self, score: float) -> str:
        if score >= 74:
            return "Constructive"
        if score >= 62:
            return "Watch"
        return "Defensive"

    def _is_watchlist_candidate(self, item: dict) -> bool:
        family = self._watchlist_family(item.get("category", ""), item.get("scheme_name", ""))
        if not family:
            return False
        scheme_name = str(item.get("scheme_name", "")).upper()
        if any(token not in scheme_name for token in WATCHLIST_NAME_REQUIRED):
            return False
        if any(token in scheme_name for token in WATCHLIST_NAME_EXCLUSIONS):
            return False
        return True

    def _history_proof_url(self) -> str:
        to_date = timezone.localdate()
        from_date = to_date - timedelta(days=WATCHLIST_HISTORY_DAYS)
        return f"{AMFI_HISTORY_URL}?frmdt={from_date.strftime('%d-%b-%Y')}&todt={to_date.strftime('%d-%b-%Y')}"

    def _external_evidence(
        self,
        *,
        source_name: str,
        source_url: str,
        summary: str,
        fetched_at,
        ttl_seconds: int,
        notes: str = "",
        status: str = "fresh",
    ) -> dict:
        stale_after = fetched_at + timedelta(seconds=ttl_seconds)
        return {
            "source_name": source_name,
            "source_url": source_url,
            "summary": summary,
            "status": status,
            "fetched_at": fetched_at.isoformat(),
            "verified_at": fetched_at.isoformat(),
            "stale_after": stale_after.isoformat(),
            "notes": notes,
        }

    def _evidence_freshness(self, items: list[dict]) -> dict:
        return freshness_snapshot(items)

    def _parse_amfi_date(self, value: str) -> date | None:
        try:
            return datetime.strptime(value.strip(), "%d-%b-%Y").date()
        except Exception:
            return None

    def _parse_nav(self, value) -> Decimal | None:
        try:
            nav = Decimal(str(value))
            if nav.is_finite() and nav > 0 and isfinite(float(nav)) and float(nav) > 0:
                return nav
        except (InvalidOperation, ValueError, TypeError, OverflowError):
            pass
        return None

    def _market_values(self, payload: dict) -> tuple[float, float] | None:
        try:
            raw = [payload.get("one_month_return_pct"), payload.get("india_vix")]
            if any(value is None or isinstance(value, bool) for value in raw):
                return None
            values = tuple(float(value) for value in raw)
            return values if all(isfinite(value) for value in values) and values[1] > 0 else None
        except (TypeError, ValueError, OverflowError):
            return None

    def _parse_zerodha_statement(self, text: str) -> List[Dict]:
        """Parse Zerodha holdings statement."""
        return self._parse_line_items(text, institution="Zerodha")

    def _parse_groww_statement(self, text: str) -> List[Dict]:
        """Parse Groww mutual fund statement."""
        return self._parse_line_items(text, institution="Groww")

    def _parse_generic_statement(self, text: str, *, broker: str = "Generic") -> List[Dict]:
        """Generic parser for unknown formats."""
        parsed = self._parse_line_items(text, institution="" if broker == "Generic" else broker)
        if parsed:
            return parsed
        investments = []
        keywords = ["mutual fund", "equity", "stock", "shares", "nav", "units", "sip"]
        for line in text.split('\n'):
            normalized = " ".join(line.split())
            if not normalized or not any(kw in normalized.lower() for kw in keywords):
                continue
            asset_type = self._guess_asset_type(normalized)
            investments.append({
                "asset_type": asset_type,
                "asset_name": normalized[:120],
                "institution": "" if broker == "Generic" else broker,
                "invested_amount": 0,
                "current_value": 0,
                "account_number": self._extract_account_hint(normalized),
            })
        return investments[:15]

    def _create_or_update_investment(self, user, inv_data: Dict):
        """Create or update investment record."""
        investment, created = Investment.objects.update_or_create(
            user=user,
            asset_name=inv_data.get("asset_name", "Unknown"),
            institution=inv_data.get("institution", ""),
            account_number=(inv_data.get("account_number") or "").strip(),
            defaults={
                "asset_type": inv_data.get("asset_type", "equity"),
                "invested_amount": investment_money(inv_data.get("invested_amount", 0)),
                "current_value": investment_money(inv_data.get("current_value", 0)),
                "annual_return_rate": inv_data.get("annual_return_rate", 0),
            },
        )
        return investment, created

    def _parse_holdings_table(self, text: str, *, broker: str):
        """Read labelled money columns; an unsafe table must not fall back to positional guesses."""
        # shortcut: labelled text tables only; expand positional layouts after representative corpus review.
        aliases = {
            "asset_name": {"symbol", "security", "fund name", "scheme name", "asset name"},
            "invested_amount": {"invested amount", "invested value", "cost value", "investment amount"},
            "current_value": {"current value", "market value", "current amount"},
            "account_number": {"account", "account number", "folio", "folio number", "demat account"},
        }
        columns = None
        header_labels = None
        holdings = {}
        source_rows = {}
        total = None
        account = ""
        conflicting_account = False
        fund_table = False

        def review(reason):
            return [], {"status": "needs_review", "reason": reason}

        def amount(value):
            # Currency/units/OCR substitutions are never inferred from a numeric-looking cell.
            if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value):
                raise ValueError("Uncertain monetary cell")
            return investment_money(value.replace(",", ""))

        for line in text.splitlines():
            if not line.strip():
                continue
            cells = [cell.strip() for cell in re.split(r"\s*\|\s*|\t+| {2,}", line.strip())]
            labels = [" ".join(cell.lower().split()) for cell in cells]
            is_header = any(label in aliases["asset_name"] for label in labels)
            if is_header:
                indices = {name: [i for i, label in enumerate(labels) if label in choices]
                           for name, choices in aliases.items()}
                if any(len(indices[name]) != 1 for name in ("asset_name", "invested_amount", "current_value")) or len(indices["account_number"]) > 1:
                    return review("Table money columns are missing or ambiguous; review the original document.")
                if any(re.search(r"\b(?:currency|denomination|ccy)\b", label) for label in labels):
                    return review("Currency-labelled tables require an approved denomination policy and source review.")
                mapped = {name: values[0] for name, values in indices.items() if values}
                if conflicting_account:
                    return review("Conflicting account headings require source review.")
                if columns is not None and labels != header_labels:
                    return review("Conflicting table headers require source review.")
                columns, width = mapped, len(cells)
                header_labels = labels
                fund_table = "fund name" in labels or "scheme name" in labels
                continue
            if columns is None:
                hint = self._extract_account_hint(line)
                if hint:
                    if account and account != hint:
                        conflicting_account = True
                    account = hint
                continue
            if len(cells) != width or total is not None:
                return review("Incomplete table rows or trailing content require source review.")
            name = cells[columns["asset_name"]]
            try:
                invested = amount(cells[columns["invested_amount"]])
                current = amount(cells[columns["current_value"]])
            except ValueError:
                return review("Uncertain table amounts require source review; no holdings were imported.")
            if name.lower() in {"total", "grand total"}:
                total = (invested, current)
                continue
            row_account = cells[columns["account_number"]] if "account_number" in columns else account
            if not re.fullmatch(r"[A-Za-z0-9-]{6,24}", row_account) or not name or len(name) > 120:
                return review("Missing or unsupported holding/account identity requires source review.")
            item = {"asset_name": name, "asset_type": "mutual_fund" if fund_table else self._guess_asset_type(name),
                    "institution": "" if broker == "Generic" else broker, "account_number": row_account,
                    "invested_amount": cells[columns["invested_amount"]].replace(",", ""),
                    "current_value": cells[columns["current_value"]].replace(",", ""), "annual_return_rate": 0}
            key = (name, row_account)
            if key in source_rows and source_rows[key] != cells:
                return review("Conflicting duplicate holdings require source review.")
            holdings[key] = item
            source_rows[key] = cells
            if len(holdings) > 30:
                return review("Table exceeds the 30-position import bound; review without partial import.")
        if columns is None:
            return None, None
        if not holdings:
            return review("No complete holdings were found in the table.")
        if total is not None and total != tuple(sum((amount(item[field]) for item in holdings.values()), start=investment_money(0))
                                                for field in ("invested_amount", "current_value")):
            return review("Table totals do not reconcile with the holdings; source review is required.")
        return list(holdings.values()), {"status": "parsed", "reason": "Labelled table amounts and account identity extracted; currency is not inferred."}

    def _parse_line_items(self, text: str, *, institution: str) -> List[Dict]:
        investments: List[Dict] = []
        seen = set()
        for line in text.splitlines():
            normalized = " ".join(line.split())
            if not normalized or len(normalized) < 6:
                continue
            numeric_values = [float(item.replace(",", "")) for item in re.findall(r"\b\d[\d,]*(?:\.\d{1,2})?\b", normalized)]
            asset_name = self._extract_asset_name(normalized)
            if not asset_name:
                continue
            asset_type = self._guess_asset_type(normalized)
            invested_amount = 0.0
            current_value = 0.0
            if len(numeric_values) >= 2:
                invested_amount = numeric_values[-2]
                current_value = numeric_values[-1]
            elif len(numeric_values) == 1:
                current_value = numeric_values[0]
            key = (asset_name.lower(), asset_type, self._extract_account_hint(normalized), round(current_value, 2), round(invested_amount, 2))
            if key in seen:
                continue
            seen.add(key)
            investments.append(
                {
                    "asset_type": asset_type,
                    "asset_name": asset_name[:120],
                    "institution": institution,
                    "account_number": self._extract_account_hint(normalized),
                    "invested_amount": invested_amount,
                    "current_value": current_value,
                    "annual_return_rate": 0,
                }
            )
        return investments[:30]

    def _extract_asset_name(self, line: str) -> str:
        cleaned = re.sub(r"\b(?:INR|RS\.?|NAV|UNITS|SHARES?|QTY|VALUE|HOLDINGS?)\b|\bRUPEES?(?=\s*\d)|\u20b9", " ", line, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b\d[\d,]*(?:\.\d{1,2})?\b", " ", cleaned)
        cleaned = " ".join(cleaned.split(" - ")[0].split())
        words = [word for word in cleaned.split() if len(word) > 2]
        if len(words) < 2:
            return ""
        return " ".join(words[:8])

    def _guess_asset_type(self, line: str) -> str:
        lowered = line.lower()
        if any(token in lowered for token in ["mutual fund", "nav", "sip", "scheme"]):
            return "mutual_fund"
        if any(token in lowered for token in ["gold", "sovereign gold"]):
            return "gold"
        if any(token in lowered for token in ["reit"]):
            return "reit"
        if any(token in lowered for token in ["bond", "debt", "fd", "debenture"]):
            return "debt"
        if any(token in lowered for token in ["crypto", "btc", "eth"]):
            return "crypto"
        if any(token in lowered for token in ["liquid", "savings", "cash"]):
            return "cash"
        return "equity"

    def _extract_account_hint(self, text: str) -> str:
        match = re.search(r"\b(?:folio|account|demat)\b[ \t]*(?:no\.?|number|id)?[ \t]*[:#-]?[ \t]*([A-Z0-9-]{6,24})\b", text, re.IGNORECASE)
        return (match.group(1) if match else "").strip()

    def _calculate_portfolio_risk_score(self, asset_breakdown: Dict, total_value: float) -> float:
        """Calculate risk score based on asset allocation."""
        risk_weights = {
            "Equity": 80,
            "Mutual Fund": 60,
            "Crypto": 100,
            "REIT": 50,
            "Debt": 20,
            "Gold": 30,
            "Cash / Liquid": 10,
        }

        weighted_risk = 0
        for asset_label, data in asset_breakdown.items():
            weight = risk_weights.get(asset_label, 50)
            weighted_risk += weight * (data["percentage"] / 100)

        return min(100, max(0, weighted_risk))

    def _calculate_diversification_score(self, asset_breakdown: Dict) -> float:
        """Calculate diversification score (higher is better)."""
        if not asset_breakdown:
            return 0

        # Shannon entropy-based diversification
        import math
        entropy = 0
        for data in asset_breakdown.values():
            p = data["percentage"] / 100
            if p > 0:
                entropy -= p * math.log(p)

        # Normalize (max entropy for 7 asset types = log(7) ÃƒÂ¢Ã¢â‚¬Â°Ã‹â€  1.95)
        max_entropy = math.log(7)
        return min(100, (entropy / max_entropy) * 100)

    def _generate_portfolio_recommendations(
        self, asset_breakdown: Dict, risk_score: float, div_score: float
    ) -> List[str]:
        """Generate actionable portfolio recommendations."""
        recommendations = []

        if div_score < 40:
            recommendations.append(
                "Low diversification detected. Consider spreading investments across multiple asset classes."
            )

        if risk_score > 75:
            recommendations.append(
                "High-risk portfolio. Consider adding debt or gold to balance risk."
            )

        if risk_score < 25:
            recommendations.append(
                "Conservative portfolio. If you're young, consider increasing equity exposure for better returns."
            )

        equity_pct = asset_breakdown.get("Equity", {}).get("percentage", 0)
        if equity_pct > 80:
            recommendations.append(
                f"Equity allocation is {equity_pct:.1f}%. Reduce concentration risk by diversifying."
            )

        if not recommendations:
            recommendations.append("Your portfolio looks well-balanced. Keep monitoring regularly.")

        return recommendations

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level."""
        if risk_score < 25:
            return "LOW"
        elif risk_score < 50:
            return "MODERATE"
        elif risk_score < 75:
            return "HIGH"
        else:
            return "VERY HIGH"

    def _calc_change(self, df) -> float:
        """Calculate percentage change in time series data."""
        if len(df) < 2:
            return 0
        return ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

    def _scrape_trending_sectors(self) -> List[Dict]:
        """Scrape trending sectors from financial news."""
        suggestions = []
        try:
            # Example: Scrape Moneycontrol or Economic Times (respect robots.txt)
            url = "https://www.moneycontrol.com/news/business/markets/"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = public_http.request("GET", url, headers=headers,
                content_types=("text/html", "application/xhtml+xml"), max_bytes=2_000_000)
            soup = BeautifulSoup(response.content, "html.parser")
            headlines = soup.find_all("h2", limit=3)
            for headline in headlines:
                text = headline.get_text(strip=True)
                if "IT" in text.upper() or "BANK" in text.upper() or "AUTO" in text.upper():
                    suggestions.append({
                        "type": "trending_sector",
                        "message": f"Market buzz: {text[:100]}",
                    })
        except Exception as exc:
            safe_error_details(exc, "Market news could not be loaded.", logger_name=__name__)

        return suggestions


# Singleton instance
portfolio_intelligence_service = PortfolioIntelligenceService()
