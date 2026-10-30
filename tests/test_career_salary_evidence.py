"""CAREER-06 synthetic salary unit, period, currency and benchmark abstention contracts."""
from django.test import SimpleTestCase

from apps.career.services.job_intelligence import job_intelligence


def openings(*salaries, location="Bengaluru, Karnataka, India"):
    return [{"company": f"Synthetic {index}", "location": location, "salary": salary,
             "url": f"https://example.test/{index}", "aggregator_name": f"feed-{index}"}
            for index, salary in enumerate(salaries)]


class SalaryTextTests(SimpleTestCase):
    def parse(self, text, **kwargs):
        return job_intelligence._parse_salary_text(text, **kwargs)

    def test_repeated_currency_range_keeps_both_bounds(self):
        for text, low, high, currency in (
                ("$120k - $150k", 120000, 150000, "USD"),
                ("₹10,00,000 - ₹15,00,000 per annum", 1000000, 1500000, "INR"),
                ("USD 90,000 to USD 110,000 per year", 90000, 110000, "USD")):
            with self.subTest(text):
                salary = self.parse(text)
                self.assertEqual((salary["salary_min"], salary["salary_max"], salary["currency"]),
                                 (low, high, currency))

    def test_conflicting_range_currencies_abstain(self):
        self.assertIsNone(self.parse("$100k - ₹150k"))

    def test_foreign_currency_is_never_relabelled_inr(self):
        for text, currency in (("€60k-70k", "EUR"), ("£55,000 per year", "GBP"),
                               ("GBP 55,000 per year", "GBP"), ("120,000-150,000 USD per year", "USD"),
                               ("80000 EUR", "EUR")):
            with self.subTest(text):
                self.assertEqual(self.parse(text)["currency"], currency)

    def test_indian_units_imply_inr_but_bare_thousands_stay_unknown(self):
        self.assertEqual(self.parse("18-22 LPA")["currency"], "INR")
        self.assertEqual(self.parse("1.2 crore")["currency"], "INR")
        self.assertEqual(self.parse("120k-150k")["currency"], "")

    def test_stated_periods_annualize_without_guessing(self):
        for text, period, annual_low in (
                ("$2,000 per week", "week", 104000), ("$400 a day", "day", 104000),
                ("$50 an hour", "hour", 104000), ("$50/hr", "hour", 104000),
                ("₹50,000 a month", "month", 600000), ("$100k/yr", "year", 100000)):
            with self.subTest(text):
                salary = self.parse(text)
                self.assertEqual(salary["period"], period)
                self.assertTrue(salary["period_stated"])
                annual = job_intelligence._annualize_salary_range(salary["salary_min"], salary["salary_max"], salary["period"])
                self.assertEqual(annual[0], annual_low)

    def test_unstated_period_is_marked_as_assumed(self):
        salary = self.parse("₹50,000")
        self.assertEqual(salary["period"], "year")
        self.assertFalse(salary["period_stated"])
        self.assertTrue(self.parse("18 LPA")["period_stated"])

    def test_page_text_ignores_money_without_salary_context(self):
        for text in ("Series B startup with $50M funding.", "Serving 10k users and 2m downloads daily traffic",
                     "Revenue of 5 cr in FY26."):
            with self.subTest(text):
                self.assertEqual(job_intelligence._extract_salary({}, text), (0.0, 0.0, "", ""))

    def test_page_text_finds_contextual_salary_after_unrelated_money(self):
        low, high, currency, period = job_intelligence._extract_salary(
            {}, "Series B startup with $50M funding. Compensation: $120k - $150k plus equity.")
        self.assertEqual((low, high, currency, period), (120000, 150000, "USD", ""))
        self.assertEqual(job_intelligence._extract_salary({}, "Great role paying ₹18 LPA")[0], 1800000)


class SalaryJsonLdTests(SimpleTestCase):
    def extract(self, base_salary):
        return job_intelligence._extract_salary_from_json_ld({"baseSalary": base_salary})

    def test_schema_org_week_and_day_units_annualize(self):
        for unit, period in (("WEEK", "week"), ("DAY", "day"), ("HOUR", "hour"), ("MONTH", "month"), ("YEAR", "year")):
            with self.subTest(unit):
                salary = self.extract({"currency": "USD", "value": {"unitText": unit, "value": 1000}})
                self.assertEqual(salary["period"], period)

    def test_unknown_unit_abstains(self):
        self.assertIsNone(self.extract({"currency": "USD", "value": {"unitText": "PROJECT", "value": 1000}}))

    def test_missing_or_invalid_currency_is_unknown_not_inr(self):
        for currency in (None, "", 42, "rupees"):
            with self.subTest(currency=currency):
                base = {"value": {"unitText": "YEAR", "value": 1000}}
                if currency is not None:
                    base["currency"] = currency
                self.assertEqual(self.extract(base)["currency"], "")

    def test_malformed_values_abstain_without_raising(self):
        for value in ("n/a", {"value": "n/a"}, {"value": "nan"}, {"value": "inf"}, {"value": -5}, {"value": True},
                      True, {"minValue": "abc", "maxValue": []}):
            with self.subTest(value=value):
                self.assertIsNone(self.extract({"currency": "USD", "value": value}))

    def test_numeric_strings_and_reversed_bounds_are_normalized(self):
        salary = self.extract({"currency": "usd", "value": {"unitText": "YEAR", "minValue": "150,000", "maxValue": 120000}})
        self.assertEqual((salary["salary_min"], salary["salary_max"], salary["currency"]), (120000, 150000, "USD"))
        self.assertTrue(salary["period_stated"])
        self.assertFalse(self.extract({"currency": "USD", "value": 1000})["period_stated"])


class CompensationBenchmarkTests(SimpleTestCase):
    def benchmark(self, *salaries, **kwargs):
        return job_intelligence.compensation_benchmark(role="Engineer", openings=openings(*salaries), **kwargs)

    def test_mixed_currencies_are_never_combined_or_converted(self):
        result = self.benchmark("INR 18 LPA", "INR 20 LPA", "USD 90000 per year")
        self.assertEqual(result["currency"], "INR")
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual((result["market_min_annual"], result["market_max_annual"]), (1900000, 1900000))
        contract = result["evidence_contract"]
        self.assertEqual(contract["currency_breakdown"], {"INR": 2, "USD": 1})
        self.assertEqual(contract["excluded_currency_count"], 1)
        self.assertTrue(contract["mixed_currency"])
        self.assertEqual(len(result["salary_observations"]), 2)
        self.assertIn("not converted", result["summary"])

    def test_equal_currency_cohorts_abstain(self):
        result = self.benchmark("INR 18 LPA", "USD 90000 per year", current_income_annual=1000000)
        self.assertFalse(result["available"])
        self.assertNotIn("market_mid_annual", result)
        self.assertIn("not converted", result["summary"])
        self.assertEqual(result["sample_count"], 0)
        self.assertEqual(result["evidence_contract"]["currency_breakdown"], {"INR": 1, "USD": 1})

    def test_foreign_benchmark_is_not_compared_with_rupee_income(self):
        result = self.benchmark("USD 90000 per year", "USD 110000 per year", current_income_annual=1000000)
        self.assertEqual(result["currency"], "USD")
        self.assertIsNone(result["comparison"])
        self.assertIn("not compared", result["summary"])

    def test_unknown_currency_is_unlabelled_uncompared_and_loses_to_known_currency(self):
        unknown = self.benchmark("120k-150k", current_income_annual=100000)
        self.assertEqual(unknown["currency"], "")
        self.assertIsNone(unknown["comparison"])
        mixed = self.benchmark("120k-150k", "INR 18 LPA")
        self.assertEqual((mixed["currency"], mixed["sample_count"]), ("INR", 1))
        self.assertEqual(mixed["evidence_contract"]["excluded_currency_count"], 1)

    def test_rupee_comparison_and_assumed_period_label_are_preserved(self):
        result = self.benchmark("INR 18 LPA", "₹20,00,000", current_income_annual=1000000)
        self.assertEqual(result["comparison"], "below_benchmark")
        self.assertEqual(result["evidence_contract"]["assumed_period_count"], 1)
        self.assertIn("did not state a pay period", result["summary"])

    def test_snapshot_without_currency_is_not_labelled_inr(self):
        from apps.career.services.job_intelligence import JobPostingSnapshot
        snapshot = JobPostingSnapshot(
            source_name="Synthetic", job_url="https://example.test/job", apply_url="https://example.test/job",
            company="Synthetic", title="Engineer", location="Remote", description="", required_skills=[],
            experience_years=0.0, salary_min=100000.0, salary_max=120000.0, salary_period="year")
        result = job_intelligence.compensation_benchmark(role="Engineer", job_snapshot=snapshot, current_income_annual=50000)
        self.assertEqual(result["currency"], "")
        self.assertIsNone(result["comparison"])

    def test_extreme_opening_value_does_not_break_the_dashboard_payload(self):
        result = job_intelligence._salary_signal_payload("$" + "9" * 40 + " per year")
        self.assertFalse(result["available"])
        self.assertTrue(self.benchmark("$" + "9" * 40 + " per year", "INR 18 LPA")["available"])


class OutcomeMedianTests(SimpleTestCase):
    def test_outcome_median_abstains_across_currencies(self):
        same = [{"salary_mid_annual": 100, "salary_currency": "USD"}, {"salary_mid_annual": 300, "salary_currency": "USD"}]
        mixed = [{"salary_mid_annual": 100, "salary_currency": "USD"}, {"salary_mid_annual": 300, "salary_currency": "INR"}]
        self.assertEqual(job_intelligence._median_salary_mid(same), 200)
        self.assertEqual(job_intelligence._median_salary_mid(mixed), 0.0)
