"""
Investment Portfolio Intelligence Service
Handles PDF imports, email scraping, portfolio analysis, and market trend suggestions.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, BinaryIO
from bs4 import BeautifulSoup
import requests
from django.db.models import Sum, F
from django.utils import timezone

from alfred_ai.services import apply_parser_learning, extract_document_text
from apps.integrations.services import verified_intelligence
from apps.investments.models import Investment


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
        raw_bytes = pdf_file.read()
        extracted = extract_document_text(raw_bytes, filename or getattr(pdf_file, "name", "portfolio.pdf"), ocr_page_limit=8)
        full_text = extracted.text or ""
        broker = self._detect_broker(full_text)

        if "ZERODHA" in broker.upper():
            parsed_investments = self._parse_zerodha_statement(full_text)
        elif "GROWW" in broker.upper():
            parsed_investments = self._parse_groww_statement(full_text)
        else:
            parsed_investments = self._parse_generic_statement(full_text, broker=broker)

        account_number = self._extract_account_hint(full_text)
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
                "investments": parsed_investments,
            },
        }

    def scrape_email_for_investments(self, user, email_config: Dict) -> Dict[str, any]:
        """
        Scrape user's email for investment-related communications.
        Looks for broker statements, mutual fund updates, etc.
        """
        # This would integrate with IMAP to fetch emails
        # For security, requires user's explicit email credentials
        # Implementation placeholder - requires OAuth2 or app-specific passwords

        return {
            "success": False,
            "message": "Email scraping requires user authentication setup",
            "instructions": "Please use PDF upload for now",
        }

    def analyze_portfolio_risk(self, user) -> Dict[str, any]:
        """Analyze portfolio risk profile and diversification."""
        investments = Investment.objects.filter(user=user)

        if not investments.exists():
            return {
                "risk_score": 0,
                "risk_level": "UNKNOWN",
                "diversification_score": 0,
                "recommendations": ["No investments found. Start investing to build wealth."],
            }

        total_value = investments.aggregate(total=Sum("current_value"))["total"] or 0

        # Calculate asset allocation
        asset_breakdown = {}
        for asset_type, label in Investment.ASSET_TYPES:
            type_value = investments.filter(asset_type=asset_type).aggregate(
                total=Sum("current_value")
            )["total"] or 0
            if type_value > 0:
                asset_breakdown[label] = {
                    "value": round(type_value, 2),
                    "percentage": round((type_value / total_value * 100), 2),
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
            "total_portfolio_value": round(total_value, 2),
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

        market_return = float(market.payload.get("one_month_return_pct") or 0)
        vix = float(market.payload.get("india_vix") or 0)
        inflation_value = float(inflation.payload.get("latest_value") or 0)

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
        user_investments = Investment.objects.filter(user=user)

        # Suggest rebalancing if needed
        if user_investments.exists():
            total_value = user_investments.aggregate(total=Sum("current_value"))["total"] or 0
            equity_percentage = (user_investments.filter(
                asset_type="equity"
            ).aggregate(total=Sum("current_value"))["total"] or 0) / total_value * 100 if total_value > 0 else 0

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
            "freshness": {
                "tracked_records": len([item for item in evidence if item]),
                "fresh_records": sum(1 for item in evidence if item and item.get("status") == "fresh"),
                "next_stale_after": min(
                    [item.get("stale_after") for item in evidence if item.get("stale_after")],
                    default="",
                ),
            },
            "last_updated": timezone.now().isoformat(),
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
            defaults={
                "asset_type": inv_data.get("asset_type", "equity"),
                "invested_amount": inv_data.get("invested_amount", 0),
                "current_value": inv_data.get("current_value", 0),
                "annual_return_rate": inv_data.get("annual_return_rate", 0),
            },
        )
        return investment, created

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
            key = (asset_name.lower(), asset_type, round(current_value, 2), round(invested_amount, 2))
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
        cleaned = re.sub(r"\b(?:INR|RS\.?|NAV|UNITS|SHARES?|QTY|VALUE|HOLDINGS?)\b", " ", line, flags=re.IGNORECASE)
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
        match = re.search(r"(?:folio|account|demat)\s*(?:no|number|id)?\s*[:#-]?\s*([A-Z0-9-]{6,24})", text, re.IGNORECASE)
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

        # Normalize (max entropy for 7 asset types = log(7) ≈ 1.95)
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
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                headlines = soup.find_all("h2", limit=3)
                for headline in headlines:
                    text = headline.get_text(strip=True)
                    if "IT" in text.upper() or "BANK" in text.upper() or "AUTO" in text.upper():
                        suggestions.append({
                            "type": "trending_sector",
                            "message": f"Market buzz: {text[:100]}",
                        })
        except Exception:
            pass

        return suggestions


# Singleton instance
portfolio_intelligence_service = PortfolioIntelligenceService()
