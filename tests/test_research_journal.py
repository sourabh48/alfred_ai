"""Investment 2.0 research journal (INVEST2-002): owner calls kept apart from holdings, settled with owner-entered prices."""
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from apps.investments.models import Investment, ResearchDecision
from apps.investments.services.research_journal import outcome
from apps.users.services import clear_user_fed_data


def _decision(**fields):
    base = dict(instrument="SYNTH", rating="buy", decided_on=date(2026, 1, 1), review_on=date(2026, 2, 1), entry_price=Decimal("100"))
    return ResearchDecision(**{**base, **fields})


class OutcomeTests(SimpleTestCase):
    def test_return_alpha_and_direction(self):
        self.assertEqual(outcome(_decision()), {"status": "pending", "review_on": "2026-02-01"})
        settled = dict(settled_on=date(2026, 2, 2), exit_price=Decimal("110"))
        plain = outcome(_decision(**settled))
        self.assertEqual((plain["return_percent"], plain["alpha_percent"], plain["measured_against"], plain["direction"]),
                         (Decimal("10.00"), None, "price only", "supported"))
        # +10% against a benchmark that rose 15%: alpha -5, so a Buy was not supported and a Sell was
        bench = dict(settled, benchmark="NIFTY", benchmark_entry=Decimal("200"), benchmark_exit=Decimal("230"))
        result = outcome(_decision(**bench))
        self.assertEqual((result["benchmark_return_percent"], result["alpha_percent"], result["direction"]),
                         (Decimal("15.00"), Decimal("-5.00"), "not_supported"))
        self.assertEqual(outcome(_decision(rating="sell", **bench))["direction"], "supported")
        self.assertEqual(outcome(_decision(rating="hold", **bench))["direction"], "not_judged")
        self.assertEqual(outcome(_decision(entry_price=Decimal("3"), settled_on=date(2026, 2, 2), exit_price=Decimal("1")))["return_percent"],
                         Decimal("-66.67"))


class ResearchJournalApiTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-research-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-research-other")
        self.client.force_login(self.owner)
        self.today = timezone.localdate()

    def create(self, **fields):
        body = {"instrument": " SYNTH ", "rating": "buy", "thesis": " Synthetic thesis ", "decided_on": (self.today - timedelta(days=30)).isoformat(),
                "review_on": (self.today - timedelta(days=1)).isoformat(), "entry_price": "100.00", **fields}
        return self.client.post("/api/investments/research/", body, content_type="application/json")

    def settle(self, pk, **body):
        return self.client.post(f"/api/investments/research/{pk}/settle/", body, content_type="application/json")

    def test_create_validates_and_never_touches_holdings(self):
        Investment.objects.create(user=self.owner, asset_name="Synthetic holding", invested_amount=Decimal("10.00"), current_value=Decimal("11.00"))
        holdings = list(Investment.objects.values())
        created = self.create(currency="")
        self.assertEqual(created.status_code, 201, created.content)
        data = created.json()
        self.assertEqual((data["instrument"], data["thesis"], data["currency"], data["outcome"]["status"]), ("SYNTH", "Synthetic thesis", None, "pending"))
        refusals = {
            "future decision": {"decided_on": (self.today + timedelta(days=1)).isoformat(), "review_on": (self.today + timedelta(days=2)).isoformat()},
            "review not after decision": {"review_on": (self.today - timedelta(days=30)).isoformat()},
            "blank thesis": {"thesis": "  "},
            "zero price": {"entry_price": "0"},
            "benchmark level without name": {"benchmark_entry": "200"},
            "unknown rating": {"rating": "moon"},
            "read-only settlement": {"lesson": "x", "settled_on": self.today.isoformat()},
        }
        for name, fields in refusals.items():
            with self.subTest(name):
                response = self.create(**fields)
                if name == "read-only settlement":  # read-only fields are ignored, never written
                    self.assertEqual((response.status_code, response.json()["settled_on"], response.json()["lesson"]), (201, None, ""))
                else:
                    self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(list(Investment.objects.values()), holdings)

    def test_settle_rules_lesson_only_after_and_owner_isolation(self):
        pending = self.create(review_on=(self.today + timedelta(days=5)).isoformat()).json()
        self.assertIn("settled_on", self.settle(pending["id"], exit_price="110").json())  # before the review date
        call = self.create(benchmark="NIFTY", benchmark_entry="200").json()
        self.assertEqual(set(self.settle(call["id"]).json()), {"exit_price", "benchmark_exit"})
        self.assertEqual(self.settle(call["id"], exit_price="110", benchmark_exit="230", settled_on=(self.today + timedelta(days=1)).isoformat()).status_code, 400)
        settled = self.settle(call["id"], exit_price="110", benchmark_exit="230", lesson=" Sector beat me ")
        self.assertEqual(settled.status_code, 200, settled.content)
        self.assertEqual((settled.json()["lesson"], settled.json()["outcome"]["alpha_percent"]), ("Sector beat me", -5.0))
        self.assertEqual(self.settle(call["id"], exit_price="120").status_code, 400)  # settles once
        self.assertEqual(self.settle(call["id"], lesson="Revised").json()["lesson"], "Revised")
        self.assertEqual(ResearchDecision.objects.get(pk=call["id"]).exit_price, Decimal("110.0000"))

        foreign = ResearchDecision.objects.create(user=self.other, instrument="THEIRS", rating="buy", thesis="t", decided_on=self.today - timedelta(days=9),
                                                  review_on=self.today - timedelta(days=2), entry_price=Decimal("1"))
        self.assertEqual(self.settle(foreign.pk, exit_price="2").status_code, 404)
        self.assertEqual(self.client.get(f"/api/investments/research/{foreign.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/investments/research/{foreign.pk}/").status_code, 404)
        self.assertEqual([row["id"] for row in self.client.get("/api/investments/research/").json()
                          if row["instrument"] == "THEIRS"], [])

    def test_lessons_recall_five_same_and_three_other_most_recent_first(self):
        def settled(instrument, days_ago, lesson="kept"):
            return ResearchDecision.objects.create(user=self.owner, instrument=instrument, rating="buy", thesis="t", lesson=lesson,
                                                   decided_on=self.today - timedelta(days=100), review_on=self.today - timedelta(days=90),
                                                   entry_price=Decimal("1"), exit_price=Decimal("2"), settled_on=self.today - timedelta(days=days_ago))
        same = [settled("SYNTH", day) for day in range(1, 8)]
        others = [settled(f"OTHER{day}", day) for day in range(1, 6)]
        settled("SYNTH", 0, lesson="")  # no lesson: not recalled
        ResearchDecision.objects.create(user=self.other, instrument="SYNTH", rating="buy", thesis="t", lesson="foreign", decided_on=self.today,
                                        review_on=self.today, entry_price=Decimal("1"), exit_price=Decimal("2"), settled_on=self.today)
        data = self.client.get("/api/investments/research/lessons/", {"instrument": "synth"}).json()
        self.assertEqual([row["id"] for row in data["same_instrument"]], [item.pk for item in same[:5]])
        self.assertEqual([row["id"] for row in data["other_instruments"]], [item.pk for item in others[:3]])
        self.assertEqual(self.client.get("/api/investments/research/lessons/").json()["other_instruments"], [])

    def test_data_reset_removes_the_journal(self):
        self.create()
        clear_user_fed_data(self.owner)
        self.assertFalse(ResearchDecision.objects.filter(user=self.owner).exists())


class ResearchJournalMigrationTests(TransactionTestCase):
    def test_forward_and_guarded_reverse_on_a_disposable_database(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before = [("investments", "0006_investment_currency") if app == "investments" else (app, name) for app, name in leaves]
        target = [("investments", "0007_research_decision") if app == "investments" else (app, name) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-research-journal-synthetic-") as directory:
            alias = "research_journal_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(Path(directory) / "journal.sqlite3")
            connections[alias] = db
            try:
                MigrationExecutor(db).migrate(target)
                apps = MigrationExecutor(db).loader.project_state(target).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(username="synthetic-journal-owner")
                row = apps.get_model("investments", "ResearchDecision").objects.using(alias).create(
                    user_id=owner.pk, instrument="SYNTH", rating="hold", thesis="t", decided_on=date(2026, 1, 1),
                    review_on=date(2026, 2, 1), entry_price="1.0000")
                with self.assertRaisesMessage(RuntimeError, "Restore the verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before)
                self.assertIn("investments_researchdecision", db.introspection.table_names())
                apps.get_model("investments", "ResearchDecision").objects.using(alias).filter(pk=row.pk).delete()
                MigrationExecutor(db).migrate(before)
                self.assertNotIn("investments_researchdecision", db.introspection.table_names())
            finally:
                db.close()
                del connections[alias]
