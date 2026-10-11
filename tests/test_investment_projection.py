from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from alfred_ai.services.materialized_cache import materialize_payload
from apps.investments.models import Investment
from apps.investments.views import _investment_revision, _project_position_value


class InvestmentProjectionFormulaTests(SimpleTestCase):
    def test_month_zero_is_the_recorded_value_without_contribution_or_growth(self):
        for annual_return in (12, 0, -12):
            with self.subTest(annual_return=annual_return):
                value = _project_position_value(
                    current_value=100000, monthly_sip=1000,
                    annual_return_rate=annual_return, months=0,
                )
                self.assertEqual(value, 100000)

    def test_one_month_adds_one_beginning_of_month_contribution(self):
        value = _project_position_value(
            current_value=100000, monthly_sip=1000,
            annual_return_rate=12, months=1,
        )
        self.assertEqual(value, 102010)

    def test_twelve_months_matches_beginning_of_month_annuity_formula(self):
        monthly_rate = 0.01
        growth_factor = (1 + monthly_rate) ** 12
        expected = 100000 * growth_factor + 1000 * (1 + monthly_rate) * (growth_factor - 1) / monthly_rate
        value = _project_position_value(
            current_value=100000, monthly_sip=1000,
            annual_return_rate=12, months=12,
        )
        self.assertAlmostEqual(value, expected, places=7)

    def test_zero_sip_only_compounds_the_recorded_value(self):
        for months in (0, 1, 12):
            with self.subTest(months=months):
                value = _project_position_value(
                    current_value=100000, monthly_sip=0,
                    annual_return_rate=12, months=months,
                )
                self.assertAlmostEqual(value, 100000 * 1.01 ** months, places=7)

    def test_zero_return_adds_exactly_one_sip_per_elapsed_month(self):
        for months in (0, 1, 12):
            with self.subTest(months=months):
                value = _project_position_value(
                    current_value=100000, monthly_sip=1000,
                    annual_return_rate=0, months=months,
                )
                self.assertEqual(value, 100000 + 1000 * months)

    def test_zero_sip_and_return_keeps_the_recorded_value(self):
        value = _project_position_value(
            current_value=100000, monthly_sip=0,
            annual_return_rate=0, months=12,
        )
        self.assertEqual(value, 100000)

    def test_negative_return_reduces_value_with_the_same_contribution_timing(self):
        monthly_rate = -0.01
        growth_factor = (1 + monthly_rate) ** 12
        expected = 100000 * growth_factor + 1000 * (1 + monthly_rate) * (growth_factor - 1) / monthly_rate
        value = _project_position_value(
            current_value=100000, monthly_sip=1000,
            annual_return_rate=-12, months=12,
        )
        self.assertAlmostEqual(value, expected, places=7)
        self.assertLess(value, 100000 + 12000)


class InvestmentProjectionAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = get_user_model().objects.create_user(
            username="investment_projection_owner", password="Pass12345!",
        )
        self.client.force_login(self.user)
        self.position = Investment.objects.create(
            user=self.user, asset_type="mutual_fund", asset_name="Projection Fund",
            current_value=100000, monthly_sip=1000, annual_return_rate=12,
        )

    def _growth(self, *, as_of=date(2026, 10, 1)):
        with patch("apps.investments.views.timezone.localdate", return_value=as_of):
            response = self.client.get("/api/investments/growth/")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_api_includes_recorded_month_zero_and_twelve_future_months(self):
        payload = self._growth(as_of=date(2026, 12, 31))
        self.assertEqual(payload["months_elapsed"], list(range(13)))
        self.assertEqual(len(payload["values"]), 13)
        self.assertEqual(payload["labels"][0:2], ["Dec 2026", "Jan 2027"])
        self.assertEqual(payload["labels"][-1], "Dec 2027")
        self.assertEqual(payload["values"][0], 100000)
        self.assertEqual(payload["values"][1], 102010)
        monthly_rate = 0.01
        growth_factor = (1 + monthly_rate) ** 12
        expected = 100000 * growth_factor + 1000 * (1 + monthly_rate) * (growth_factor - 1) / monthly_rate
        self.assertEqual(payload["values"][-1], round(expected, 2))
        self.assertEqual(payload["assumptions"]["month_zero"], "recorded_current_value")
        self.assertEqual(payload["assumptions"]["contribution_timing"], "beginning_of_month")
        self.assertEqual(payload["assumptions"]["annual_return_rate_source"], "user_entered")
        self.assertEqual(payload["assumptions"]["monthly_return_rate_formula"], "annual_return_rate / 1200")

    def test_api_aggregates_only_owned_positions(self):
        Investment.objects.create(
            user=self.user, asset_type="cash", asset_name="Owned Cash",
            current_value=500, monthly_sip=20, annual_return_rate=0,
        )
        other = get_user_model().objects.create_user(username="projection_other")
        Investment.objects.create(
            user=other, asset_type="equity", asset_name="Other Holding",
            current_value=999999, monthly_sip=9999, annual_return_rate=99,
        )
        payload = self._growth()
        self.assertEqual(payload["values"][0], 100500)
        self.assertEqual(payload["values"][1], 102530)

    def test_empty_portfolio_is_zero_for_all_thirteen_points(self):
        self.position.delete()
        self.assertEqual(self._growth()["values"], [0] * 13)

    def test_cached_projection_refreshes_after_position_edit(self):
        first = self._growth()
        cached = self._growth()
        self.assertFalse(first["_materialized"]["cached"])
        self.assertTrue(cached["_materialized"]["cached"])
        response = self.client.patch(
            f"/api/investments/{self.position.pk}/",
            {"current_value": 200000, "monthly_sip": 0, "annual_return_rate": 0},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        edited = self._growth()
        self.assertFalse(edited["_materialized"]["cached"])
        self.assertEqual(edited["values"], [200000] * 13)

    def test_local_month_rollover_refreshes_labels_without_position_changes(self):
        october = self._growth(as_of=date(2026, 10, 31))
        november = self._growth(as_of=date(2026, 11, 1))
        self.assertFalse(november["_materialized"]["cached"])
        self.assertNotEqual(october["_materialized"]["revision"], november["_materialized"]["revision"])
        self.assertEqual(november["labels"][0], "Nov 2026")
        self.assertEqual(november["labels"][-1], "Nov 2027")

    def test_old_cached_growth_schema_is_not_served(self):
        materialize_payload(
            namespace="investments-growth", user_id=self.user.pk,
            revision=_investment_revision(self.user), ttl_seconds=90,
            builder=lambda: {"labels": ["Old Month"], "values": [102010]},
        )
        payload = self._growth()
        self.assertFalse(payload["_materialized"]["cached"])
        self.assertEqual(len(payload["values"]), 13)
        self.assertEqual(payload["values"][0], 100000)
