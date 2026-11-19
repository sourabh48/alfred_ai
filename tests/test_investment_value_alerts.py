"""INV-07 value alerts: limits in the holding's own currency, unknown never counts as crossed, owner-only, bot reports."""
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.investments.models import Investment
from apps.ml_engine.services import task_bots
from tests.test_persistent_memory import SyntheticEmbeddings


class InvestmentValueAlertTests(TestCase):
    URL = "/api/investments/value-alerts/"

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-value-alert-synthetic-")))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.root / "vault")))
        self.enterContext(patch("apps.ml_engine.services.persistent_memory.OllamaEmbeddings", return_value=SyntheticEmbeddings()))
        users = get_user_model().objects
        self.owner, self.other = users.create_user(username="synthetic-value-owner"), users.create_user(username="synthetic-value-other")
        self.client.force_login(self.owner)
        self.row = Investment.objects.create(user=self.owner, asset_name="SYNTHETIC-VALUE-PRIVATE", asset_type="equity",
                                             current_value="1000.00", currency="INR")

    def get(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        return response.json()

    def post(self, action, **kwargs):
        return self.client.post(self.URL, {"action": action, "revision": self.get()["revision"], **kwargs}, content_type="application/json")

    def item(self):
        return self.get()["items"][0]

    def test_limits_are_checked_in_the_holdings_own_currency(self):
        self.assertEqual(self.post("set", id=self.row.pk, below="900", above="1500.005").status_code, 200)
        self.assertEqual((self.item()["status"], self.item()["below"], self.item()["above"], self.item()["currency"]),
                         ("inside", "900.00", "1500.01", "INR"))
        Investment.objects.filter(pk=self.row.pk).update(current_value="899.99")
        self.assertEqual(self.item()["status"], "below")
        Investment.objects.filter(pk=self.row.pk).update(current_value="1500.02")
        self.assertEqual(self.item()["status"], "above")
        Investment.objects.filter(pk=self.row.pk).update(currency="USD")  # never converted: the limit must be set again
        self.assertEqual(self.item()["status"], "unknown")
        Investment.objects.filter(pk=self.row.pk).update(currency="INR", current_value="0")  # no value is unknown, not zero
        self.assertEqual(self.item()["status"], "unknown")

    def test_a_fund_price_that_is_not_current_is_not_checked(self):
        Investment.objects.filter(pk=self.row.pk).update(asset_type="mutual_fund", amfi_scheme_code="120503", units="10",
            current_value="10.00", nav_date=timezone.localdate() - timedelta(days=30))
        self.post("set", id=self.row.pk, below="500")
        self.assertEqual(self.item()["status"], "unknown")
        self.assertIn("fund price is not current", self.item()["reason"])

    def test_bad_limits_other_peoples_holdings_and_stale_revisions_are_refused(self):
        theirs = Investment.objects.create(user=self.other, asset_name="SYNTHETIC-OTHER", asset_type="equity", current_value="5")
        for kwargs in ({}, {"below": "-1"}, {"below": "abc"}, {"below": 1.5}, {"below": "900", "above": "900"},
                       {"below": "1e9999"}, {"below": "1", "colour": "red"}):
            self.assertEqual(self.post("set", id=self.row.pk, **kwargs).status_code, 400, kwargs)
        self.assertEqual(self.post("set", id=theirs.pk, below="1").status_code, 400)
        self.assertEqual(self.client.post(self.URL, {"action": "set", "revision": 99, "id": self.row.pk, "below": "1"},
                                          content_type="application/json").status_code, 409)
        self.assertEqual(self.get()["items"], [])
        self.assertNotIn(theirs.pk, [h["id"] for h in self.get()["holdings"]])

    def test_clear_delete_and_the_vault_keeps_no_names(self):
        self.post("set", id=self.row.pk, below="777.77")
        self.client.force_login(self.other)
        self.assertEqual(self.get()["items"], [])  # each owner sees only their own limits
        self.client.force_login(self.owner)
        for path in self.root.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"SYNTHETIC-VALUE-PRIVATE", path.read_bytes())
                self.assertNotIn(b"777.77", path.read_bytes())
        self.assertEqual(self.post("clear", id=self.row.pk).status_code, 200)
        self.assertEqual(self.get()["items"], [])
        self.post("set", id=self.row.pk, below="1")
        self.row.delete()
        self.assertEqual(self.get()["items"], [])

    def test_the_bot_reports_only_crossed_limits_and_never_trades(self):
        today = timezone.localdate()
        self.post("set", id=self.row.pk, below="900")
        self.assertIsNone(task_bots.run(self.owner, "value_alerts", today))
        Investment.objects.filter(pk=self.row.pk).update(current_value="850.50")
        proposal = task_bots.run(self.owner, "value_alerts", today)
        item = proposal["items"][0]
        self.assertEqual(item["title"], "SYNTHETIC-VALUE-PRIVATE: below your limit")
        self.assertIn("Now ₹850.50 (the value you recorded), below your limit of ₹900.00", item["detail"])
        self.assertIn("never buys or sells", item["detail"])
        self.assertIsNone(item["action"])
        self.assertIsNone(task_bots.run(self.other, "value_alerts", today))
        self.assertEqual(Investment.objects.get(pk=self.row.pk).current_value, 850.50)  # read only
