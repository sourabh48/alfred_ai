"""FAMILY-07 synthetic contracts: missing inputs are labelled, never scored as measured risk."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.career.models import CareerJobAnalysis, CareerProfile
from apps.expenses.models import BankAccount
from apps.risk.models import RiskSignal
from apps.risk.serializers import RiskSignalSerializer
from apps.risk.services.risk_intelligence import risk_intelligence


def market_payload(risk_score=0, evidence=()):
    return {"risk_score": risk_score, "layoff_news": [], "job_market_news": [], "insights": [], "evidence": list(evidence),
            "macro_context": {"unemployment": {"latest_value": None}, "inflation": {"latest_value": None},
                              "market": {"one_month_return_pct": None, "india_vix": None}}}


class RiskSignalValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("risk_valid", password="synthetic-pass-123")
        self.client.force_login(self.user)

    def post(self, **changes):
        body = {"layoff_risk": 10, "illness_risk": 20, "relocation_risk": 30, **changes}
        raw = "{" + ",".join(f'"{key}":{value}' for key, value in body.items()) + "}"
        return self.client.post("/api/risk/", raw, content_type="application/json")

    def test_out_of_range_and_non_finite_values_are_rejected_without_a_record(self):
        for field in ("layoff_risk", "illness_risk", "relocation_risk"):
            for value in ("-1", "100.5", "5000", "NaN", "Infinity", "-Infinity", '"NaN"'):
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.post(**{field: value}).status_code, 400)
        self.assertFalse(RiskSignal.objects.exists())

    def test_boundaries_are_accepted_and_owner_is_server_assigned(self):
        other = get_user_model().objects.create_user("risk_valid_other", password="synthetic-pass-123")
        response = self.post(layoff_risk=0, illness_risk=100, relocation_risk=99.5, user=other.pk)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RiskSignal.objects.get().user, self.user)

    def test_omitted_fields_keep_the_model_default(self):
        response = self.client.post("/api/risk/", {"layoff_risk": 5}, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RiskSignal.objects.get().illness_risk, 0)

    def test_legacy_out_of_range_record_stays_readable_and_unrewritten(self):
        row = RiskSignal.objects.create(user=self.user, layoff_risk=500, illness_risk=-5, relocation_risk=300)
        self.assertEqual(RiskSignalSerializer(row).data["layoff_risk"], 500)
        response = self.client.get("/api/risk/")
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual((row.layoff_risk, row.illness_risk, row.relocation_risk), (500, -5, 300))


class RiskEvidenceCoverageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("risk_coverage", password="synthetic-pass-123")

    def outlook(self, *, user=None, market=None, role="Synthetic analyst"):
        if role:
            CareerProfile.objects.update_or_create(user=user or self.user, defaults={"role": role, "experience_years": 3, "skills": ""})
        market = market or market_payload()
        with patch("apps.risk.services.risk_intelligence.job_intelligence.market_outlook", return_value=market),                 patch("apps.risk.services.risk_intelligence.verified_intelligence.macro_context",
                      return_value={"payload": market["macro_context"], "evidence": market["evidence"]}):
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

    def test_no_job_role_means_no_news_search_and_no_career_score(self):
        evidence = {"title": "Synthetic market", "source_url": "https://example.test/market", "status": "fresh"}
        with patch("apps.risk.services.risk_intelligence.job_intelligence.market_outlook") as outlook:
            result, items = self.outlook(market=market_payload(risk_score=48, evidence=[evidence]), role="")
        outlook.assert_not_called()
        self.assertEqual(items["career"]["coverage"]["status"], "insufficient_data")
        self.assertEqual(items["career"]["score"], 0)
        self.assertIn("Job role not set in Career; job market not scored", items["career"]["drivers"])
        self.assertEqual(result["summary"]["highest_label"], "No data")
        self.assertEqual(result["related_news"], [])

    def test_all_insufficient_summary_abstains(self):
        with patch("apps.risk.services.risk_intelligence._category_coverage",
                   return_value={"status": "insufficient_data", "available_inputs": [], "missing_inputs": ["x"]}):
            result, _ = self.outlook()
        self.assertEqual(result["summary"]["highest_label"], "No data")
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

    def test_behavior_log_older_than_the_window_is_not_current_health_evidence(self):
        signal = BehavioralSignal.objects.create(user=self.user, stress_score=9, sleep_hours=3, work_hours=14)
        BehavioralSignal.objects.filter(pk=signal.pk).update(timestamp=timezone.now() - timedelta(days=70))
        result, items = self.outlook()
        self.assertEqual(items["health"]["score"], 0)
        self.assertEqual(items["health"]["coverage"]["status"], "insufficient_data")
        self.assertIsNone(result["module_signals"]["average_stress"])

    def test_manual_snapshot_is_observed_and_explicit_zero_counts(self):
        RiskSignal.objects.create(user=self.user, layoff_risk=0, illness_risk=0, relocation_risk=0)
        BehavioralSignal.objects.create(user=self.user, stress_score=1, sleep_hours=8, work_hours=8)
        _, items = self.outlook()
        self.assertEqual(items["health"]["coverage"]["status"], "observed")
        self.assertIn("Manual illness snapshot 0/100", items["health"]["drivers"])

    def test_abstained_job_fit_is_not_scored_as_a_gap(self):
        CareerJobAnalysis.objects.create(user=self.user, job_url="https://example.test/a", fit_score=0,
                                         extracted_payload={"fit": {"score_status": "UNAVAILABLE"}})
        _, items = self.outlook()
        self.assertEqual(items["career"]["score"], 0)
        self.assertIn("Job fit", items["career"]["coverage"]["missing_inputs"])

    def test_missing_job_fit_adds_no_career_risk(self):
        _, items = self.outlook()
        self.assertEqual(items["career"]["score"], 0)
        self.assertIn("Job-fit evidence unavailable; not scored", items["career"]["drivers"])

    def test_failed_feeds_are_not_market_evidence(self):
        failed = {"title": "Synthetic feed", "source_url": "https://example.test/failed", "status": "failed"}
        market = {**market_payload(evidence=[failed]), "insights": ["No strong external layoff spike was found."]}
        result, items = self.outlook(market=market)
        self.assertEqual(items["career"]["coverage"]["status"], "insufficient_data")
        self.assertIn("External market evidence unavailable", items["career"]["drivers"])
        self.assertEqual(result["summary"]["highest_label"], "No data")
        self.assertFalse(any("layoff spike" in line for line in result["insights"]))

    def test_stale_feed_still_counts_as_market_evidence(self):
        stale = {"title": "Synthetic feed", "source_url": "https://example.test/stale", "status": "stale"}
        _, items = self.outlook(market=market_payload(risk_score=20, evidence=[stale]))
        self.assertIn("External market evidence", items["career"]["coverage"]["available_inputs"])
        self.assertIn("External market risk 20/100", items["career"]["drivers"])

    def test_unavailable_inflation_is_not_reported_as_zero(self):
        _, items = self.outlook()
        self.assertIn("Inflation evidence unavailable", items["relocation"]["drivers"])
        market = market_payload()
        market["macro_context"]["inflation"]["latest_value"] = 5.649
        _, items = self.outlook(market=market)
        self.assertIn("Inflation 5.6%", items["relocation"]["drivers"])

    def test_no_vehicle_reports_unknown_not_zero_compliance(self):
        result, _ = self.outlook()
        self.assertIsNone(result["module_signals"]["mobility_document_compliance"])
        self.assertIsNone(result["module_signals"]["mobility_condition_score"])

    def test_valid_documents_are_vehicle_evidence_and_a_vehicle_without_them_is_a_real_zero(self):
        summary = {"critical_faults": 0, "expired_documents": 0, "expiring_documents": 0, "latest_condition_score": 0,
                   "document_compliance_score": 100, "managed_vehicle_count": 1}
        with patch("apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
                   return_value={"summary": summary, "pending_tasks": []}):
            result, items = self.outlook()
        self.assertEqual(items["mobility"]["coverage"]["status"], "observed")
        self.assertEqual(result["module_signals"]["mobility_document_compliance"], 100)
        summary["document_compliance_score"] = 0
        with patch("apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
                   return_value={"summary": summary, "pending_tasks": []}):
            result, items = self.outlook()
        self.assertEqual(items["mobility"]["coverage"]["status"], "insufficient_data")
        self.assertEqual(result["module_signals"]["mobility_document_compliance"], 0)

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

    def test_income_without_a_bank_account_makes_no_liquid_cash_claim(self):
        self.user.monthly_income = 50000
        self.user.save(update_fields=["monthly_income"])
        result, _ = self.outlook()
        self.assertFalse(any("Liquid cash" in line for line in result["insights"]), result["insights"])
        self.assertIsNone(result["grounding"]["history"]["liquid_cash"])

    def test_recorded_low_liquid_cash_is_still_reported(self):
        self.user.monthly_income = 50000
        self.user.save(update_fields=["monthly_income"])
        BankAccount.objects.create(user=self.user, account_number="SYNTHETIC-RISK-1", current_balance="1000.00")
        result, _ = self.outlook()
        self.assertTrue(any("Liquid cash" in line for line in result["insights"]), result["insights"])
        self.assertEqual(result["grounding"]["history"]["liquid_cash"], 1000.0)

    def test_account_without_an_entered_balance_or_only_credit_is_unknown_cash(self):
        self.user.monthly_income = 50000
        self.user.rent_or_emi = 20000
        self.user.save(update_fields=["monthly_income", "rent_or_emi"])
        for number, kind in (("SYNTHETIC-RISK-NULL", "savings"), ("SYNTHETIC-RISK-CARD", "credit")):
            BankAccount.objects.create(user=self.user, account_number=number, account_type=kind, current_balance=None)
            result, items = self.outlook()
            with self.subTest(kind):
                self.assertIsNone(result["grounding"]["history"]["liquid_cash"])
                self.assertFalse(any("Liquid cash" in line for line in result["insights"]))
                self.assertIn("Emergency runway unknown", items["financial"]["drivers"])
                self.assertEqual(items["financial"]["score"], 40 * 0.7)

    def test_no_vehicle_shows_no_measured_fault_counts(self):
        _, items = self.outlook()
        self.assertEqual(items["mobility"]["drivers"][:1], ["No vehicle records"])
        self.assertFalse(any(line.startswith(("Critical faults", "Expired documents")) for line in items["mobility"]["drivers"]))

    def test_insufficient_category_drives_no_news_search_or_action(self):
        from apps.family.models import Dependent
        for index in range(6):
            Dependent.objects.create(user=self.user, name=f"Synthetic {index}", age=10, relation="child")
        market = market_payload()
        market["macro_context"]["unemployment"]["latest_value"] = 10
        with patch("apps.risk.services.risk_intelligence.verified_intelligence.google_news_search") as search:
            result, items = self.outlook(market=market)
        self.assertGreaterEqual(items["financial"]["score"], 35)
        self.assertEqual(items["financial"]["coverage"]["status"], "insufficient_data")
        search.assert_not_called()
        self.assertEqual(result["action_items"], [])

    def test_manual_snapshot_older_than_ninety_days_is_not_counted(self):
        signal = RiskSignal.objects.create(user=self.user, layoff_risk=90, illness_risk=90, relocation_risk=90)
        RiskSignal.objects.filter(pk=signal.pk).update(timestamp=timezone.now() - timedelta(days=91))
        result, items = self.outlook()
        self.assertEqual(items["career"]["score"], 0)
        self.assertEqual(items["health"]["coverage"]["status"], "insufficient_data")
        self.assertTrue(items["career"]["drivers"][0].endswith("older than 90 days; not counted"))
        self.assertIsNone(result["grounding"]["history"]["latest_manual_layoff"])
        self.assertEqual(len(result["history"]), 1)
        RiskSignal.objects.filter(pk=signal.pk).update(timestamp=timezone.now() - timedelta(days=89))
        _, items = self.outlook()
        self.assertEqual(items["career"]["score"], 31.5)

    def test_news_search_gets_the_role_but_not_the_analyzed_company(self):
        CareerJobAnalysis.objects.create(user=self.user, job_url="https://example.test/job", company="Synthetic Employer Ltd",
                                         fit_score=0, extracted_payload={"fit": {"score_status": "UNAVAILABLE"}})
        CareerProfile.objects.create(user=self.user, role="Synthetic analyst", experience_years=3, skills="")
        with patch("apps.risk.services.risk_intelligence.job_intelligence.market_outlook", return_value=market_payload()) as outlook:
            risk_intelligence.build_outlook(self.user)
        self.assertEqual(outlook.call_args.args, ("Synthetic analyst", ""))

    def test_required_documents_not_added_are_listed_but_not_scored(self):
        summary = {"critical_faults": 0, "expired_documents": 0, "expiring_documents": 0, "latest_condition_score": 0,
                   "document_compliance_score": 0, "managed_vehicle_count": 1, "missing_required_documents": 3}
        with patch("apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
                   return_value={"summary": summary, "pending_tasks": []}):
            _, items = self.outlook()
        self.assertEqual(items["mobility"]["score"], 0)
        self.assertIn("Required documents not yet added: 3", items["mobility"]["drivers"])

    def test_unrecorded_inputs_are_not_reported_as_zero_in_grounding(self):
        result, _ = self.outlook()
        history = result["grounding"]["history"]
        for key in ("average_stress", "average_sleep", "latest_manual_layoff", "latest_manual_illness", "latest_manual_relocation"):
            with self.subTest(key):
                self.assertIsNone(history[key])
        RiskSignal.objects.create(user=self.user, layoff_risk=0, illness_risk=0, relocation_risk=0)
        result, _ = self.outlook()
        self.assertEqual(result["grounding"]["history"]["latest_manual_layoff"], 0)

    def test_no_rated_category_has_no_highest_score(self):
        with patch("apps.risk.services.risk_intelligence._category_coverage",
                   return_value={"status": "insufficient_data", "available_inputs": [], "missing_inputs": ["x"]}):
            result, _ = self.outlook()
        self.assertIsNone(result["summary"]["highest_score"])
        self.assertIsNone(result["summary"]["overall_average"])
        self.assertIsNone(result["outlook"]["average"])

    def test_output_states_uncalibrated_heuristic_and_stays_owner_isolated(self):
        other = get_user_model().objects.create_user("risk_other", password="synthetic-pass-123")
        BehavioralSignal.objects.create(user=other, stress_score=9, sleep_hours=3, work_hours=14)
        RiskSignal.objects.create(user=other, layoff_risk=90, illness_risk=90, relocation_risk=90)
        result, items = self.outlook()
        self.assertEqual(items["health"]["coverage"]["status"], "insufficient_data")
        self.assertFalse(result["calibration"]["calibrated"])
        self.assertIn("not a diagnosis", result["calibration"]["statement"])
