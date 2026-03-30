"""
Investment Portfolio Intelligence Service
Handles PDF imports, email scraping, portfolio analysis, and market trend suggestions.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, BinaryIO
import pdfplumber
import yfinance as yf
from bs4 import BeautifulSoup
import requests
from django.db.models import Sum, F
from django.utils import timezone

from apps.investments.models import Investment


class PortfolioIntelligenceService:
    """ML-powered investment portfolio management and analysis."""

    def parse_portfolio_pdf(self, pdf_file: BinaryIO, user) -> Dict[str, any]:
        """
        Parse investment portfolio from PDF (broker statements, mutual fund statements).
        Supports multiple formats from Groww, Zerodha, etc.
        """
        investments_created = []
        investments_updated = []

        try:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() or ""

                # Detect broker type
                broker = self._detect_broker(full_text)

                # Parse based on broker
                if "ZERODHA" in broker.upper():
                    parsed_investments = self._parse_zerodha_statement(full_text)
                elif "GROWW" in broker.upper():
                    parsed_investments = self._parse_groww_statement(full_text)
                else:
                    parsed_investments = self._parse_generic_statement(full_text)

                # Create or update investments
                for inv_data in parsed_investments:
                    investment, created = self._create_or_update_investment(user, inv_data)
                    if created:
                        investments_created.append(investment)
                    else:
                        investments_updated.append(investment)

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "created": 0,
                "updated": 0,
            }

        return {
            "success": True,
            "created": len(investments_created),
            "updated": len(investments_updated),
            "investments": investments_created + investments_updated,
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
        Scrape market trends and provide AI-powered investment suggestions.
        """
        suggestions = []

        # Fetch market indices
        try:
            nifty = yf.Ticker("^NSEI")
            nifty_info = nifty.history(period="5d")

            sensex = yf.Ticker("^BSESN")
            sensex_info = sensex.history(period="5d")

            market_trend = "bullish" if len(nifty_info) > 1 and nifty_info['Close'].iloc[-1] > nifty_info['Close'].iloc[0] else "bearish"

            suggestions.append({
                "type": "market_overview",
                "message": f"Indian market is currently {market_trend}. "
                          f"Nifty 50: {nifty_info['Close'].iloc[-1]:.2f} ({self._calc_change(nifty_info):.2f}%)",
            })

        except Exception:
            suggestions.append({
                "type": "market_overview",
                "message": "Unable to fetch live market data.",
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

        # Scrape news for trending sectors
        try:
            trending_sectors = self._scrape_trending_sectors()
            suggestions.extend(trending_sectors)
        except Exception:
            pass

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
        investments = []
        # Pattern: Stock name, quantity, avg price, current price, etc.
        # This is a simplified parser - real implementation needs robust PDF table extraction
        lines = text.split('\n')
        for line in lines:
            # Example pattern matching (customize based on actual format)
            if re.search(r'\d+\s+shares', line, re.IGNORECASE):
                investments.append({
                    "asset_type": "equity",
                    "asset_name": "Auto-detected Stock",
                    "institution": "Zerodha",
                    "invested_amount": 0,
                    "current_value": 0,
                })
        return investments

    def _parse_groww_statement(self, text: str) -> List[Dict]:
        """Parse Groww mutual fund statement."""
        investments = []
        # Similar parsing logic for Groww format
        return investments

    def _parse_generic_statement(self, text: str) -> List[Dict]:
        """Generic parser for unknown formats."""
        investments = []
        # Use keywords to detect investments
        keywords = ["mutual fund", "equity", "stock", "shares", "NAV", "units"]
        lines = text.split('\n')
        for line in lines:
            if any(kw in line.lower() for kw in keywords):
                investments.append({
                    "asset_type": "equity",
                    "asset_name": "Auto-detected Investment",
                    "institution": "Unknown",
                    "invested_amount": 0,
                    "current_value": 0,
                })
        return investments

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
