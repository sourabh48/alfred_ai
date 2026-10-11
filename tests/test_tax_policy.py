"""Official-table boundaries, relief ordering and dated tax API regressions."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.integrations.services import verified_intelligence
from apps.loans.models import Loan, LoanPaymentHistory
from apps.ml_engine.services.tax_optimizer import tax_optimizer
from apps.ml_engine.services.tax_policy import POLICY_VERSION, TaxPolicyError, calculate_income_tax, get_policy


D = Decimal


class TaxPolicyTests(SimpleTestCase):
    def ordinary(self, income, regime="new", **kwargs):
        return calculate_income_tax(income, regime, income_type="ordinary", **kwargs)

    def test_zero_and_salary_standard_deduction_limited_to_income(self):
        for regime in ("old", "new"):
            for income in (0, 1, 10000):
                with self.subTest(regime=regime, income=income):
                    result = calculate_income_tax(income, regime)
                    self.assertEqual(result["standard_deduction"], income)
                    self.assertEqual(result["taxable_income"], 0)
                    self.assertEqual(result["final_tax"], 0)
                    self.assertEqual(result["cess"], 0)

    def test_all_slab_boundaries_one_rupee_below_exact_and_above(self):
        # Independent cumulative tax values at the published slab boundaries,
        # before rebates/cess. Rates on either side detect boundary drift.
        cases = {
            "old": [(250000, 0, 0, 5), (500000, 12500, 5, 20), (1000000, 112500, 20, 30)],
            "new": [(400000, 0, 0, 5), (800000, 20000, 5, 10), (1200000, 60000, 10, 15),
                    (1600000, 120000, 15, 20), (2000000, 200000, 20, 25), (2400000, 300000, 25, 30)],
        }
        for regime, rows in cases.items():
            for boundary, tax, lower_rate, upper_rate in rows:
                for offset, expected in ((-1, D(tax) - D(lower_rate) / 100),
                                         (0, D(tax)), (1, D(tax) + D(upper_rate) / 100)):
                    with self.subTest(regime=regime, boundary=boundary, offset=offset):
                        self.assertEqual(self.ordinary(boundary + offset, regime)["base_tax"], expected)

    def test_old_rebate_precedes_cess_and_has_no_rebate_marginal_relief(self):
        for income in (499999, 500000):
            result = self.ordinary(income, "old")
            self.assertEqual(result["rebate_87a"], result["base_tax"])
            self.assertEqual(result["cess"], 0)
            self.assertEqual(result["final_tax"], 0)
        result = self.ordinary(500001, "old")
        self.assertEqual(result["rebate_87a"], 0)
        self.assertEqual(result["rebate_marginal_relief"], 0)
        self.assertEqual(result["final_tax"], D("13000.21"))

    def test_new_rebate_and_marginal_relief_before_cess(self):
        for income in (1199999, 1200000):
            result = self.ordinary(income)
            self.assertEqual(result["final_tax"], 0)
            self.assertEqual(result["cess"], 0)
        result = self.ordinary(1200001)
        self.assertEqual(result["base_tax"], D("60000.15"))
        self.assertEqual(result["rebate_marginal_relief"], D("59999.15"))
        self.assertEqual(result["cess"], D("0.04"))
        self.assertEqual(result["final_tax"], D("1.04"))

    def test_official_marginal_relief_examples(self):
        for income, tax_before_cess in ((1210000, 10000), (1225000, 25000), (1250000, 50000)):
            with self.subTest(income=income):
                result = self.ordinary(income)
                self.assertEqual(result["tax_before_cess"], tax_before_cess)
                self.assertEqual(result["final_tax"], D(tax_before_cess) * D("1.04"))
        self.assertEqual(self.ordinary(1270589)["rebate_marginal_relief"], 0)

    def test_salary_and_non_salary_are_distinct(self):
        self.assertEqual(calculate_income_tax(1275000, "new")["final_tax"], 0)
        self.assertEqual(calculate_income_tax(1500000, "new")["final_tax"], 97500)
        self.assertEqual(calculate_income_tax(1500000, "old")["final_tax"], 257400)
        self.assertEqual(self.ordinary(1500000)["final_tax"], 109200)
        self.assertEqual(self.ordinary(1500000)["standard_deduction"], 0)

    def test_surcharge_and_relief_at_all_thresholds(self):
        expected = {
            "old": [(5000000, 1365000), (10000000, 3217500), (20000000, 6951750), (50000000, 19256250)],
            "new": [(5000000, 1123200), (10000000, 2951520), (20000000, 6673680)],
        }
        for regime, rows in expected.items():
            for threshold, final in rows:
                with self.subTest(regime=regime, threshold=threshold):
                    below = self.ordinary(threshold - 1, regime)
                    exact = self.ordinary(threshold, regime)
                    above = self.ordinary(threshold + 1, regime)
                    self.assertEqual(exact["final_tax"], final)
                    self.assertLess(below["final_tax"], exact["final_tax"])
                    self.assertEqual(above["final_tax"], D(final) + D("1.04"))
                    self.assertGreater(above["surcharge_marginal_relief"], 0)
                    self.assertEqual(exact["surcharge_marginal_relief"], 0)

    def test_surcharge_caps_and_cess_after_surcharge(self):
        new = self.ordinary(60000000)
        old = self.ordinary(60000000, "old")
        self.assertEqual(new["surcharge_rate"], D("0.25"))
        self.assertEqual(old["surcharge_rate"], D("0.37"))
        self.assertEqual(new["surcharge_marginal_relief"], 0)
        for regime, expected in (("new", 1578720), ("old", 1844700)):
            self.assertEqual(self.ordinary(6000000, regime)["final_tax"], expected)

    def test_nonresident_does_not_get_rebate_or_rebate_relief(self):
        self.assertEqual(self.ordinary(1200000, resident=False)["final_tax"], 62400)
        self.assertEqual(self.ordinary(1200001, resident=False)["rebate_marginal_relief"], 0)
        self.assertEqual(self.ordinary(500000, "old", resident=False)["final_tax"], 13000)

    def test_age_exemptions_only_for_resident_old_regime(self):
        for age, base in (("under_60", 2500), ("60_to_79", 0), ("80_plus", 0)):
            self.assertEqual(self.ordinary(300000, "old", age_group=age)["base_tax"], base)
        self.assertEqual(self.ordinary(500000, "old", age_group="80_plus")["base_tax"], 0)
        self.assertEqual(self.ordinary(300000, "old", age_group="80_plus", resident=False)["base_tax"], 2500)

    def test_deduction_caps_and_regime_eligibility(self):
        deductions = {"80C": 200000, "80CCD(1B)": 60000, "80CCD(2)": 30000}
        old = calculate_income_tax(2000000, "old", deductions)
        new = calculate_income_tax(2000000, "new", deductions)
        self.assertEqual(old["total_deductions"], 230000)
        self.assertEqual(old["capped_deductions"], {"80C": 50000, "80CCD(1B)": 10000})
        self.assertEqual(new["total_deductions"], 30000)
        self.assertEqual(new["ignored_deductions"], {"80C": 200000, "80CCD(1B)": 60000})
        comparison = tax_optimizer.compare_regimes(2000000, deductions)
        self.assertEqual(comparison["new_regime"]["total_deductions"], 30000)

    def test_unsupported_years_and_mismatch_are_never_substituted(self):
        for options in ({"financial_year": "2024-25"}, {"financial_year": "2026-27"},
                        {"assessment_year": "2025-26"}, {"assessment_year": "2027-28"},
                        {"financial_year": "2025-26", "assessment_year": "2027-28"},
                        {"financial_year": ""}):
            with self.subTest(options=options), self.assertRaises(TaxPolicyError):
                calculate_income_tax(1000000, **options)
        result = calculate_income_tax(1000000, assessment_year="2026-27")
        self.assertEqual(result["financial_year"], "2025-26")

    def test_invalid_income_deductions_and_scope(self):
        for bad in (-1, True, None, "", "bad", "NaN", "Infinity", "-Infinity", "1e1000000", "9" * 100, {}, []):
            with self.subTest(bad=bad), self.assertRaises(TaxPolicyError):
                calculate_income_tax(bad)
        for deductions in ([], {"unknown": 10}, {"80C": -1}, {"80D": "NaN"}):
            with self.subTest(deductions=deductions), self.assertRaises(TaxPolicyError):
                calculate_income_tax(1000000, deductions=deductions)
        for options in ({"regime": "NEW"}, {"special_rate_income": 1}, {"income_type": "capital_gains"},
                        {"resident": "true"}, {"age_group": "unknown"}):
            with self.subTest(options=options), self.assertRaises(TaxPolicyError):
                calculate_income_tax(1000000, **options)

    def test_decimal_values_and_official_policy_metadata(self):
        result = calculate_income_tax("1275000.01", "new")
        self.assertIsInstance(result["base_tax"], Decimal)
        self.assertEqual(result["final_tax"], D("0.01"))
        self.assertEqual(result["policy"]["version"], POLICY_VERSION)
        self.assertEqual(result["policy"]["verified_at"], "2026-10-01")
        self.assertEqual(result["policy"]["freshness"], "STATIC_REFERENCE")
        self.assertEqual(get_policy("new").metadata()["rebate_limit"], 60000)


class TaxOverviewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="tax-policy-user", monthly_income=200000)
        self.client.force_login(self.user)
        self.url = "/api/integrations/tax/overview/"

    def tearDown(self):
        cache.clear()

    def test_api_keeps_comparison_and_savings_on_same_income_and_year(self):
        # First-time reference creation changes the existing dashboard revision.
        # Seed those local references before testing reuse of a stable revision.
        verified_intelligence.tax_regime_reference()
        verified_intelligence.nps_tax_reference()
        verified_intelligence.ppf_reference()
        response = self.client.get(self.url, {"annual_income": "1500000", "financial_year": "2025-26"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["regime_comparison"]["new_regime"]["final_tax"], 97500)
        self.assertEqual(data["tax_savings"]["current_tax"], data["regime_comparison"]["old_regime"]["final_tax"])
        self.assertEqual(data["inputs"]["assessment_year"], "2026-27")
        self.assertEqual(data["tax_policy"]["freshness"], "STATIC_REFERENCE")
        cached = self.client.get(self.url, {"annual_income": "1500000", "financial_year": "2025-26"}).json()
        self.assertTrue(cached["_materialized"]["cached"])
        self.assertEqual(cached["regime_comparison"], data["regime_comparison"])

    def test_invalid_requests_return_400_even_after_valid_cached_request(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        for params in ({"annual_income": "NaN"}, {"annual_income": "-1"}, {"annual_income": "bad"},
                       {"rent_paid": "Infinity"}, {"annual_income": ""}, {"financial_year": "2024-25"},
                       {"financial_year": "2026-27"}, {"assessment_year": "2027-28"}):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())

    def test_assessment_year_selection_and_default_are_explicit(self):
        data = self.client.get(self.url, {"assessment_year": "2026-27"}).json()
        self.assertEqual(data["tax_policy"]["financial_year"], "2025-26")
        self.assertEqual(data["inputs"]["financial_year"], "2025-26")

    def test_payment_deductions_use_selected_year(self):
        loan = Loan.objects.create(user=self.user, loan_type="home", lender="Test", principal=1000000,
                                   interest_rate=8, emi=10000, tenure_months=120, remaining_balance=900000,
                                   start_date=date(2025, 4, 1))
        for payment_date, principal in ((date(2025, 4, 1), 10000), (date(2026, 3, 31), 20000),
                                        (date(2026, 4, 1), 90000)):
            LoanPaymentHistory.objects.create(loan=loan, payment_date=payment_date, amount=principal,
                                               principal_component=principal, match_status="matched")
        data = self.client.get(self.url, {"financial_year": "2025-26"}).json()
        self.assertEqual(data["deductions"]["80C"], 30000)

    def test_reference_uses_versioned_rules_and_refresh_does_not_change_rule_date(self):
        from apps.integrations.models import VerifiedExternalInsight

        legacy = VerifiedExternalInsight.objects.create(
            scope="tax", cache_key="india-income-tax-regimes", title="Previous rules",
            source_name="Income Tax Department", source_url="https://www.incometax.gov.in/iec/foportal/",
            payload={"new_regime_basic_exemption": 300000}, status="stale", stale_after=timezone.now(),
        )
        result = verified_intelligence.tax_regime_reference()
        self.assertEqual(result.payload["new_regime_basic_exemption"], 400000)
        record = VerifiedExternalInsight.objects.get(cache_key=f"india-income-tax-regimes:{POLICY_VERSION}")
        self.assertEqual(verified_intelligence._refresh_record(record), "refreshed")
        record.refresh_from_db()
        self.assertEqual(record.payload["rules_verified_at"], "2026-10-01")
        legacy.refresh_from_db()
        self.assertFalse(legacy.is_active)
        self.assertEqual(legacy.payload["new_regime_basic_exemption"], 300000)

    def test_other_users_income_is_not_reused(self):
        self.client.get(self.url)
        other = get_user_model().objects.create_user(username="other-tax-policy", monthly_income=10000)
        self.client.force_login(other)
        data = self.client.get(self.url).json()
        self.assertEqual(data["regime_comparison"]["new_regime"]["final_tax"], 0)

    def test_anonymous_access_requires_authentication(self):
        self.client.logout()
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
