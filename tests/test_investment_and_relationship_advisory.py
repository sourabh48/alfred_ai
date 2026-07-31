from datetime import date, timedelta
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.expenses.models import Expense
from apps.investments.models import Investment
from apps.loans.models import Loan, LoanPaymentHistory
from apps.relationship.models import RelationshipProfile


class InvestmentAndRelationshipAdvisoryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="advisory_user",
            password="Pass12345!",
            monthly_income=125000,
            rent_or_emi=30000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)
        Investment.objects.create(
            user=self.user,
            asset_type="equity",
            asset_name="Index Fund",
            institution="Groww",
            invested_amount=180000,
            current_value=210000,
            monthly_sip=10000,
            annual_return_rate=12,
            risk_level="Moderate",
        )
        Investment.objects.create(
            user=self.user,
            asset_type="debt",
            asset_name="Debt Fund",
            institution="Zerodha",
            invested_amount=80000,
            current_value=83500,
            monthly_sip=3000,
            annual_return_rate=7,
            risk_level="Low",
        )
        Expense.objects.create(
            user=self.user,
            amount=42000,
            classification="expense",
            category="household",
            payment_mode="UPI",
            merchant="Household",
            description="Monthly spend",
            raw_description="Monthly spend",
            transaction_date="2026-03-20",
            direction="debit",
            source="manual",
        )
        Loan.objects.create(
            user=self.user,
            lender="HDFC",
            loan_type="personal",
            principal=400000,
            interest_rate=11.5,
            emi=9800,
            tenure_months=48,
            remaining_balance=275000,
            start_date="2025-08-01",
            is_active=True,
        )
        RelationshipProfile.objects.create(
            user=self.user,
            partner_name="Ananya",
            partner_financial_score=74,
            partner_savings_habits=4,
            compatibility_score=78,
        )

    def test_investment_summary_exposes_materialized_grounding(self):
        with patch(
            "apps.investments.services.portfolio_intelligence.verified_intelligence.market_snapshot",
            return_value=_insight({"one_month_return_pct": 2.6, "india_vix": 13.4}, "Yahoo Finance", "Market snapshot is fresh."),
        ), patch(
            "apps.investments.services.portfolio_intelligence.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 4.9, "latest_year": 2025}, "World Bank", "Inflation snapshot is fresh."),
        ), patch(
            "apps.investments.services.portfolio_intelligence.requests.get",
            side_effect=requests.Timeout("AMFI timeout"),
        ):
            first = self.client.get("/api/investments/summary/")
            second = self.client.get("/api/investments/summary/")

        self.assertEqual(first.status_code, 200)
        payload = first.json()
        self.assertFalse(payload["_materialized"]["cached"])
        self.assertEqual(payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertEqual(len(payload["grounding"]["evidence"]), 2)
        self.assertIn("Portfolio guidance is grounded", payload["grounding"]["notes"][0])
        self.assertFalse(payload["watchlist"]["available"])
        self.assertTrue(second.json()["_materialized"]["cached"])

    def test_relationship_alignment_exposes_grounding_and_materialization(self):
        with patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 5.2, "latest_year": 2025}, "World Bank", "Inflation reference is fresh."),
        ), patch(
            "apps.relationship.services.relationship_intelligence.verified_intelligence.market_snapshot",
            return_value=_insight({"one_month_return_pct": 1.8, "india_vix": 12.8}, "Yahoo Finance", "Market snapshot is fresh."),
        ), patch(
            "apps.relationship.services.relationship_intelligence.relationship_model_predictor.predict_score",
            return_value=76.0,
        ):
            first = self.client.get("/api/relationship/alignment/")
            second = self.client.get("/api/relationship/alignment/")

        self.assertEqual(first.status_code, 200)
        payload = first.json()
        self.assertFalse(payload["_materialized"]["cached"])
        self.assertEqual(payload["compatibility"], "Good")
        self.assertEqual(len(payload["factors"]), 4)
        self.assertEqual(payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertTrue(payload["grounding"]["freshness"]["proof_complete"])
        self.assertTrue(payload["grounding"]["proof_contract"]["complete"])
        self.assertGreater(payload["alignment_score"], 0)
        self.assertTrue(second.json()["_materialized"]["cached"])

    def test_home_loan_contributes_asset_backed_position_to_financial_intelligence(self):
        home_loan = Loan.objects.create(
            user=self.user,
            lender="SBI",
            loan_type="home",
            principal=4000000,
            home_down_payment=500000,
            home_other_upfront_payments=150000,
            interest_rate=8.5,
            emi=36500,
            tenure_months=240,
            remaining_balance=3200000,
            start_date="2024-04-01",
            is_active=True,
            status="active",
        )
        LoanPaymentHistory.objects.create(
            loan=home_loan,
            payment_date="2026-03-10",
            amount=36500,
            principal_component=8500,
            interest_component=28000,
            principal_paid=8500,
            interest_paid=28000,
            remaining_balance=3200000,
            match_status="matched",
        )

        payload = build_financial_intelligence(self.user)
        loan_summary_response = self.client.get("/api/loans/summary/")
        self.assertEqual(loan_summary_response.status_code, 200)
        loan_summary = loan_summary_response.json()["summary"]["home_ownership_summary"]

        self.assertEqual(payload["balance_sheet"]["home_loan_asset_proxy_total"], 4650000.0)
        self.assertEqual(payload["balance_sheet"]["home_loan_upfront_cash_total"], 650000.0)
        self.assertEqual(len(payload["balance_sheet"]["home_ownership_positions"]), 1)
        position = payload["balance_sheet"]["home_ownership_positions"][0]
        self.assertEqual(position["financed_asset_value"], 4000000.0)
        self.assertEqual(position["property_acquisition_cost"], 4650000.0)
        self.assertEqual(position["down_payment"], 500000.0)
        self.assertEqual(position["other_upfront_payments"], 150000.0)
        self.assertEqual(position["upfront_cash_invested"], 650000.0)
        self.assertEqual(position["current_loan_balance"], 3200000.0)
        self.assertEqual(position["estimated_principal_repaid"], 800000.0)
        self.assertEqual(position["equity_built"], 1450000.0)
        self.assertEqual(position["principal_paid_recorded"], 8500.0)
        self.assertEqual(position["interest_and_cost_paid_recorded"], 28000.0)
        self.assertEqual(payload["loan_portfolio"]["home_ownership_summary"]["down_payment_total"], 500000.0)
        self.assertEqual(payload["loan_portfolio"]["home_ownership_summary"]["other_upfront_payments_total"], 150000.0)
        self.assertEqual(payload["loan_portfolio"]["home_ownership_summary"]["upfront_cash_invested_total"], 650000.0)
        self.assertEqual(payload["loan_portfolio"]["home_ownership_summary"]["property_acquisition_cost_total"], 4650000.0)
        self.assertEqual(payload["loan_portfolio"]["home_ownership_summary"]["equity_built_total"], 1450000.0)
        self.assertEqual(loan_summary["down_payment_total"], 500000.0)
        self.assertEqual(loan_summary["other_upfront_payments_total"], 150000.0)
        self.assertTrue(
            any(item["label"] == "Home property acquisition-cost base (proxy)" for item in payload["balance_sheet"]["assets"])
        )

    def test_home_purchase_price_drives_derived_down_payment_and_equity_math(self):
        home_loan = Loan.objects.create(
            user=self.user,
            lender="SBI",
            loan_type="home",
            principal=4000000,
            home_purchase_price=4500000,
            home_down_payment=0,
            home_other_upfront_payments=150000,
            interest_rate=8.5,
            emi=36500,
            tenure_months=240,
            remaining_balance=3200000,
            start_date="2024-04-01",
            is_active=True,
            status="active",
        )
        LoanPaymentHistory.objects.create(
            loan=home_loan,
            payment_date="2026-03-10",
            amount=36500,
            principal_component=8500,
            interest_component=28000,
            principal_paid=8500,
            interest_paid=28000,
            remaining_balance=3200000,
            match_status="matched",
        )

        payload = build_financial_intelligence(self.user)
        position = payload["balance_sheet"]["home_ownership_positions"][0]
        summary = payload["loan_portfolio"]["home_ownership_summary"]

        self.assertEqual(position["purchase_price"], 4500000.0)
        self.assertEqual(position["down_payment"], 500000.0)
        self.assertEqual(position["other_upfront_payments"], 150000.0)
        self.assertEqual(position["property_acquisition_cost"], 4650000.0)
        self.assertEqual(position["equity_built"], 1450000.0)
        self.assertEqual(summary["purchase_price_total"], 4500000.0)
        self.assertEqual(summary["down_payment_total"], 500000.0)
        self.assertEqual(summary["property_acquisition_cost_total"], 4650000.0)

    def test_investment_pdf_import_creates_upload_and_linked_holdings(self):
        imported_investment = Investment.objects.create(
            user=self.user,
            asset_type="mutual_fund",
            asset_name="Axis Bluechip Fund",
            institution="Groww",
            account_number="FOLIO12345",
            invested_amount=50000,
            current_value=56200,
            annual_return_rate=11.2,
        )
        report = SimpleUploadedFile("portfolio.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

        with patch(
            "apps.investments.views.portfolio_intelligence_service.parse_portfolio_pdf",
            return_value={
                "success": True,
                "created": 1,
                "updated": 0,
                "investments": [imported_investment],
                "parser_status": "parsed",
                "confidence": 0.88,
                "broker": "Groww",
                "summary": "1 investment position was extracted from the Groww document.",
                "extracted_text": "Groww holdings statement",
                "payload": {
                    "broker_name": "Groww",
                    "account_number": "FOLIO12345",
                    "investments": [
                        {
                            "asset_type": "mutual_fund",
                            "asset_name": "Axis Bluechip Fund",
                            "institution": "Groww",
                            "account_number": "FOLIO12345",
                            "invested_amount": 50000,
                            "current_value": 56200,
                        }
                    ],
                },
            },
        ):
            response = self.client.post("/api/investments/import-pdf/", data={"file": report})

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["upload"]["parser_status"], "parsed")
        self.assertEqual(payload["upload"]["broker_name"], "Groww")
        self.assertEqual(len(payload["investments"]), 1)
        self.assertEqual(payload["investments"][0]["asset_name"], "Axis Bluechip Fund")
        self.assertEqual(payload["upload"]["linked_investments"][0]["asset_name"], "Axis Bluechip Fund")

    def test_investment_summary_exposes_short_horizon_watchlist_with_proof(self):
        cache.clear()
        latest_report = "\n".join([
            "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date",
            "Open Ended Schemes(Equity Scheme - Flexi Cap Fund)",
            "Axis Mutual Fund",
            "120000;INF000000001;INF000000002;Axis Flexi Cap Fund - Direct Plan - Growth;18.4000;31-Mar-2026",
            "Open Ended Schemes(Hybrid Scheme - Balanced Advantage Fund)",
            "ICICI Prudential Mutual Fund",
            "120001;INF000000003;INF000000004;ICICI Prudential Balanced Advantage Fund - Direct Plan - Growth;22.1500;31-Mar-2026",
        ])
        history_lines = [
            "Scheme Code;Scheme Name;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Net Asset Value;Repurchase Price;Sale Price;Date",
            "Open Ended Schemes(Equity Scheme - Flexi Cap Fund)",
            "Axis Mutual Fund",
        ]
        axis_navs = [15.00, 15.08, 15.16, 15.25, 15.34, 15.45, 15.58, 15.66, 15.74, 15.89, 16.02, 16.11, 16.26, 16.32, 16.48, 16.56, 16.67, 16.74, 16.83, 16.92, 17.05, 17.12, 17.23, 17.31, 17.44, 17.58, 17.69, 17.77, 17.89, 18.01, 18.12, 18.19, 18.26, 18.31, 18.36, 18.40]
        icici_navs = [20.00, 20.04, 20.09, 20.15, 20.18, 20.24, 20.31, 20.35, 20.40, 20.46, 20.50, 20.55, 20.58, 20.61, 20.67, 20.72, 20.78, 20.83, 20.90, 20.96, 21.03, 21.08, 21.16, 21.22, 21.31, 21.40, 21.48, 21.57, 21.63, 21.72, 21.81, 21.89, 21.95, 22.01, 22.08, 22.15]
        start_date = date(2026, 2, 24)
        dates = [(start_date + timedelta(days=index)).strftime("%d-%b-%Y") for index in range(36)]
        for nav, nav_date in zip(axis_navs, dates):
            history_lines.append(f"120000;Axis Flexi Cap Fund - Direct Plan - Growth;INF000000001;INF000000002;{nav:.4f};;;{nav_date}")
        history_lines.extend([
            "Open Ended Schemes(Hybrid Scheme - Balanced Advantage Fund)",
            "ICICI Prudential Mutual Fund",
        ])
        for nav, nav_date in zip(icici_navs, dates):
            history_lines.append(f"120001;ICICI Prudential Balanced Advantage Fund - Direct Plan - Growth;INF000000003;INF000000004;{nav:.4f};;;{nav_date}")
        history_report = "\n".join(history_lines)

        def fake_requests_get(url, params=None, timeout=0):
            if "NAVOpen.txt" in url:
                return _text_response(latest_report)
            return _text_response(history_report)

        with patch(
            "apps.investments.services.portfolio_intelligence.requests.get",
            side_effect=fake_requests_get,
        ), patch(
            "apps.investments.services.portfolio_intelligence.verified_intelligence.market_snapshot",
            return_value=_insight({"one_month_return_pct": 2.6, "india_vix": 13.4}, "Yahoo Finance", "Market snapshot is fresh."),
        ), patch(
            "apps.investments.services.portfolio_intelligence.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 4.9, "latest_year": 2025}, "World Bank", "Inflation snapshot is fresh."),
        ), patch(
            "apps.investments.services.portfolio_intelligence.verified_intelligence.google_news_search",
            return_value=_insight({"items": [{"title": "Fund category inflows remain constructive"}]}, "Google News", "Recent coverage is fresh."),
        ):
            response = self.client.get("/api/investments/summary/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["watchlist"]["available"])
        self.assertGreaterEqual(len(payload["watchlist"]["items"]), 1)
        first_item = payload["watchlist"]["items"][0]
        self.assertIn("proof", first_item)
        self.assertGreaterEqual(len(first_item["proof"]), 3)
        self.assertEqual(payload["watchlist"]["algorithm"]["window_days"], 60)
        self.assertIn("guardrail", payload["watchlist"]["algorithm"])

    def test_recommendation_overview_suppresses_credit_cards_and_personal_loans(self):
        with patch(
            "apps.integrations.views.verified_intelligence.market_snapshot",
            return_value=_insight({"one_month_return_pct": 2.6, "india_vix": 13.4}, "Yahoo Finance", "Market snapshot is fresh."),
        ), patch(
            "apps.integrations.views.verified_intelligence.world_bank_indicator",
            return_value=_insight({"latest_value": 4.9, "latest_year": 2025}, "World Bank", "Inflation snapshot is fresh."),
        ):
            response = self.client.get("/api/integrations/recommendations/overview/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["credit_cards"]["enabled"])
        self.assertFalse(payload["loans"]["enabled"])
        self.assertEqual(payload["credit_cards"]["recommendations"], [])
        self.assertEqual(payload["loans"]["recommendations"], [])
        self.assertEqual(len(payload["disabled_modules"]), 2)
        self.assertEqual(payload["credit_cards"]["grounding"]["history"]["policy_state"], "disabled")
        self.assertEqual(payload["loans"]["grounding"]["history"]["policy_state"], "disabled")
        self.assertGreaterEqual(payload["credit_cards"]["grounding"]["freshness"]["tracked_records"], 1)
        self.assertGreaterEqual(payload["loans"]["grounding"]["freshness"]["tracked_records"], 1)
        self.assertEqual(payload["investments"]["grounding"]["freshness"]["tracked_records"], 2)
        self.assertEqual(payload["insurance"]["grounding"]["freshness"]["tracked_records"], 1)
        self.assertEqual(payload["grounding"]["freshness"]["tracked_records"], 2)
        self.assertEqual(len(payload["grounding"]["modules"]), 4)
        self.assertEqual(payload["grounding"]["modules"][0]["key"], "investments")
        self.assertEqual(payload["grounding"]["modules"][1]["key"], "insurance")
        self.assertEqual(payload["grounding"]["modules"][2]["key"], "credit_cards")
        self.assertEqual(payload["grounding"]["modules"][2]["status"], "disabled")
        self.assertEqual(payload["grounding"]["modules"][3]["key"], "personal_loans")


def _insight(payload, source_name, summary):
    class DummyInsight:
        def __init__(self):
            self.payload = payload
            self.evidence = {
                "source_name": source_name,
                "summary": summary,
                "status": "fresh",
                "stale_after": _future_stale_after(),
                "source_url": "https://example.com/proof",
            }

    return DummyInsight()


def _future_stale_after():
    return (timezone.now() + timedelta(days=2)).isoformat()


def _text_response(text):
    class DummyResponse:
        def __init__(self, body):
            self.text = body

        def raise_for_status(self):
            return None

    return DummyResponse(text)
