from decimal import Decimal as D

from django.test import SimpleTestCase

from apps.ml_engine.services.capital_gains import calculate_capital_gains_tax
from apps.ml_engine.services.tax_policy import TaxPolicyError


def sale(asset_type, bought, sold, cost, sale_value, stt_paid=True, **extra):
    return {"asset_type": asset_type, "bought": bought, "sold": sold, "cost": cost,
            "sale_value": sale_value, "stt_paid": stt_paid, **extra}


class CapitalGainsTaxTests(SimpleTestCase):
    def test_long_term_equity_above_exemption_with_new_regime_marginal_relief(self):
        # Salary 10,00,000 - 75,000 = 9,25,000 slab income: tax 32,500. Gain 3,00,000 - 1,25,000 at 12.5% = 21,875.
        # Total 12,25,000: relief 32,500 - 25,000 = 7,500 against slab tax only (s.156(3), s.198(7)).
        result = calculate_capital_gains_tax([sale("listed_equity", "2024-01-10", "2026-06-01", 100000, 400000)],
                                             annual_income=1000000, regime="new")
        self.assertEqual(result["slab_tax"], D("32500"))
        self.assertEqual(result["special_rate_tax"]["s198"], D("21875"))
        self.assertEqual(result["rebate"], D("7500"))
        self.assertEqual(result["final_tax"], D("48750.00"))

    def test_unused_basic_exemption_and_old_regime_rebate_cover_short_term_equity(self):
        # Old regime: 2,00,000 - 50,000 = 1,50,000 slab income leaves 1,00,000 of the 2,50,000 exemption.
        # Short-term equity gain 1,50,000 - 1,00,000 = 50,000 at 20% = 10,000; total 3,00,000 gets the s.156(1) rebate.
        result = calculate_capital_gains_tax([sale("listed_equity", "2026-01-05", "2026-05-05", 100000, 250000)],
                                             annual_income=200000, regime="old")
        self.assertEqual(result["basic_exemption_used_against_gains"]["s196"], D("100000"))
        self.assertEqual(result["special_rate_tax"]["s196"], D("10000"))
        self.assertEqual(result["final_tax"], D("0.00"))

    def test_short_term_loss_goes_where_it_saves_most(self):
        # A 50,000 short-term equity loss saves 20% against gold gains on slab rates, but only 12.5% against equity.
        result = calculate_capital_gains_tax([
            sale("listed_equity", "2026-01-05", "2026-05-05", 150000, 100000),
            sale("listed_equity", "2023-01-05", "2026-05-05", 100000, 300000),
            sale("other", "2025-12-01", "2026-06-01", 100000, 200000, stt_paid=False),
        ], annual_income=2000000, regime="new")
        self.assertEqual(result["loss_setoffs"], [{"loss_from": "s196", "set_off_against": "slab", "amount": D("50000")}])
        self.assertEqual(result["net_gains"]["slab"], D("50000"))
        self.assertEqual(result["unused_losses"], {"short_term": D("0"), "long_term": D("0")})

    def test_long_term_loss_never_reduces_short_term_gains(self):
        result = calculate_capital_gains_tax([
            sale("other", "2020-01-01", "2026-06-01", 300000, 200000, stt_paid=False),
            sale("other", "2026-01-01", "2026-06-01", 100000, 200000, stt_paid=False),
        ], annual_income=1500000, regime="new")
        self.assertEqual(result["net_gains"]["slab"], D("100000"))
        self.assertEqual(result["unused_losses"]["long_term"], D("100000"))

    def test_holding_period_boundary_is_more_than_twelve_months(self):
        short = calculate_capital_gains_tax([sale("listed_equity", "2025-04-10", "2026-04-10", 100, 200)])
        long = calculate_capital_gains_tax([sale("listed_equity", "2025-04-10", "2026-04-11", 100, 200)])
        self.assertEqual((short["sales"][0]["bucket"], long["sales"][0]["bucket"]), ("s196", "s198"))
        gold = calculate_capital_gains_tax([sale("other", "2024-06-01", "2026-06-01", 100, 200, stt_paid=False)])
        self.assertEqual(gold["sales"][0]["bucket"], "slab")  # exactly 24 months is still short-term

    def test_debt_funds_are_always_slab_rate_and_equity_without_stt_is_section_197(self):
        result = calculate_capital_gains_tax([
            sale("debt_fund", "2023-05-01", "2026-06-01", 100000, 150000, stt_paid=False),
            sale("listed_equity", "2020-05-01", "2026-06-01", 100000, 150000, stt_paid=False),
        ], annual_income=1500000)
        self.assertEqual([s["bucket"] for s in result["sales"]], ["slab", "s197"])

    def test_land_bought_before_23_july_2024_uses_the_cheaper_indexed_option(self):
        # 12.5% of 30,00,000 = 3,75,000; 20% of (50,00,000 - 32,00,000 indexed) = 3,60,000, so 15,000 is ignored.
        result = calculate_capital_gains_tax([sale("land_building", "2015-06-01", "2026-06-01", 2000000, 5000000,
                                                   stt_paid=False, indexed_cost=3200000)],
                                             annual_income=1500000, regime="new")
        self.assertEqual(result["land_indexation_relief"], D("15000.000"))
        self.assertEqual(result["special_rate_tax"]["s197"], D("360000.000"))
        self.assertEqual(result["needs_review"], [])

    def test_unsupported_inputs_are_refused(self):
        for bad in (sale("listed_equity", "2025-01-01", "2026-03-31", 1, 2),          # sold before tax year 2026-27
                    sale("debt_fund", "2022-01-01", "2026-06-01", 1, 2, stt_paid=False),
                    sale("listed_equity", "2020-01-01", "2026-06-01", 1, 2, indexed_cost=1),
                    sale("listed_equity", "2026-07-01", "2026-06-01", 1, 2),
                    sale("crypto", "2026-01-01", "2026-06-01", 1, 2)):
            with self.assertRaises(TaxPolicyError):
                calculate_capital_gains_tax([bad])
        with self.assertRaises(TaxPolicyError):
            calculate_capital_gains_tax([])
