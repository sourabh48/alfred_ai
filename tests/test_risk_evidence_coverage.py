"""FAMILY-07 synthetic contracts: missing inputs are labelled, never scored as measured risk."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.behavioral.models import BehavioralSignal
from apps.career.models import CareerJobAnalysis
from apps.risk.models import RiskSignal
from apps.risk.services.risk_intelligence import risk_intelligence


def market_payload(risk_score=0, evidence=()):
    return {"risk_score": risk_score, "layoff_news": [], "job_market_news": [], "insights": [], "evidence": list(evidence),
            "macro_context": {"unemployment": {"latest_value": None}, "inflation": {"latest_value": None},
                              "market": {"one_month_return_pct": None, "india_vix": None}}}


class RiskEvidenceCoverageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("risk_coverage", password="synthetic-pass-123")

    def outlook(self, *, user=None, market=None):
        with patch("apps.risk.services.risk_intelligence.job_intelligence.market_outlook",
                   return_value=market or market_payload()):
            result = risk_intelligence.build_outlook(user or self.user)
        return result, {item["key"]: item for item in result["consolidated_risks"]}

    def test_account_without_data_has_no_phantom_risk(self):
        evidence = {"title": "Synthetic market", "source_url": "https://example.test/market", "status": "fresh"}
        result, items = self.outlook(market=market_payload(evidence=[evidence]))
        for key in ("financial", "health", "relocation", "mobility"):
            with self.subTest(key):
                self.assertEqual(items[key]["coverage"]["status"], "insufficient_data")
                self.assertEqual(items[key]["level"], "insufficient_data")
        self.assertEqual(items["health"]["score"], 0)
        self.assertEqual(items["mobility"]["score"], 0)
        self.assertEqual(items["financial"]["score"], 0)
        self.assertEqual(result["summary"]["highest_label"], "Career / Layoff")
        self.assertEqual(result["summary"]["insufficient_category_count"], 4)
        self.assertNotIn("Average sleep 0.0h", items["health"]["drivers"])
        self.assertNotIn("Condition score 0/100", items["mobility"]["drivers"])
        self.assertEqual(result["action_items"], [])

    def test_all_insufficient_summary_abstains(self):
        with patch("apps.risk.services.risk_intelligence._category_coverage",
                   return_value={"status": "insufficient_data", "available_inputs": [], "missing_inputs": ["x"]}):
            result, _ = self.outlook()
        self.assertEqual((result["summary"]["highest_label"], result["summary"]["highest_score"]), ("No data", 0))
        self.assertEqual(result["summary"]["overall_average"], 0)
        self.assertEqual(result["outlook"]["average"], 0)
        self.assertFalse(any("Highest consolidated risk" in line for line in result["insights"]))

    def test_recorded_short_sleep_and_stress_still_raise_health_risk(self):
        BehavioralSignal.objects.create(user=self.user, stress_score=8, sleep_hours=4, work_hours=11)
        _, items = self.outlook()
        self.assertEqual(items["health"]["score"], 8*5.5 + 2*8 + 2*3)
        self.assertEqual(items["health"]["coverage"]["status"], "partial")
        self.assertIn("Behavior log", items["health"]["coverage"]["available_inputs"])
        self.assertIn("Manual illness snapshot", items["health"]["coverage"]["missing_inputs"])

    def test_unset_sleep_field_is_not_zero_hours(self):
        BehavioralSignal.objects.create(user=self.user, stress_score=2)
        _, items = self.outlook()
        self.assertEqual(items["health"]["score"], 2*5.5)
        self.assertIn("No sleep hours recorded", items["health"]["drivers"])

    def test_manual_snapshot_is_observed_and_explicit_zero_counts(self):
        RiskSignal.objects.create(user=self.user, layoff_risk=0, illness_risk=0, relocation_risk=0)
        BehavioralSignal.objects.create(user=self.user, stress_score=1, sleep_hours=8, work_hours=8)
        _, items = self.outlook()
        self.assertEqual(items["health"]["coverage"]["status"], "observed")
        self.assertIn("Manual illness snapshot 0/100", items["health"]["drivers"])

    def test_abstained_job_fit_uses_the_labelled_fallback_not_a_full_gap(self):
        CareerJobAnalysis.objects.create(user=self.user, job_url="https://example.test/a", fit_score=0,
                                         extracted_payload={"fit": {"score_status": "UNAVAILABLE"}})
        _, items = self.outlook()
        self.assertEqual(items["career"]["score"], round(24*0.15, 1))
        self.assertIn("Job fit", items["career"]["coverage"]["missing_inputs"])

    def test_vehicle_condition_counts_when_present(self):
        snapshot = {"summary": {"critical_faults": 0, "expired_documents": 0, "expiring_documents": 0,
                                "latest_condition_score": 40, "document_compliance_score": 100}, "pending_tasks": []}
        with patch("apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot", return_value=snapshot):
            _, items = self.outlook()
        self.assertEqual(items["mobility"]["score"], 12.5)
        self.assertEqual(items["mobility"]["coverage"]["status"], "observed")

    def test_trends_do_not_claim_stability_without_history(self):
        _, items = self.outlook()
        self.assertEqual(items["career"]["trend"], "insufficient_history")
        self.assertEqual(items["financial"]["trend"], "not_tracked")
        self.assertEqual(items["mobility"]["trend"], "not_tracked")
        for layoff in (50, 50, 10, 10):
            RiskSignal.objects.create(user=self.user, layoff_risk=layoff, illness_risk=0, relocation_risk=0)
        _, items = self.outlook()
        self.assertEqual(items["career"]["trend"], "falling")

    def test_output_states_uncalibrated_heuristic_and_stays_owner_isolated(self):
        other = get_user_model().objects.create_user("risk_other", password="synthetic-pass-123")
        BehavioralSignal.objects.create(user=other, stress_score=9, sleep_hours=3, work_hours=14)
        RiskSignal.objects.create(user=other, layoff_risk=90, illness_risk=90, relocation_risk=90)
        result, items = self.outlook()
        self.assertEqual(items["health"]["coverage"]["status"], "insufficient_data")
        self.assertFalse(result["calibration"]["calibrated"])
        self.assertIn("not a diagnosis", result["calibration"]["statement"])
