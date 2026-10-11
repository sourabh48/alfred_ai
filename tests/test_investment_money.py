from decimal import Decimal
from importlib import import_module
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase

from apps.investments.money import investment_money, investment_total_float
from apps.investments.models import Investment, InvestmentImportDocument, InvestmentMoneySnapshot
from apps.investments.serializers import InvestmentSerializer
from apps.investments.views import _investment_allocation_payload, _portfolio_risk
from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service
from alfred_ai.services.document_review import _apply_investment_correction, _upsert_retry_investments
from apps.users.services import clear_user_fed_data


class InvestmentMoneyBoundaryTests(SimpleTestCase):
    def test_half_up_signed_cents_and_unbounded_virtual_totals(self):
        for source, expected in (("2.675", "2.68"), ("-1.005", "-1.01"), ("0.005", "0.01")):
            self.assertEqual(investment_money(source), Decimal(expected))
        self.assertEqual(investment_total_float(Decimal("1999999999999.98")), 1999999999999.98)

    def test_invalid_money_rejected(self):
        for value in (True, False, "NaN", "Infinity", "-Infinity", "1e1000", "999999999999.995", "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                investment_money(value)


class InvestmentMoneyRuntimeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="money-owner")
        self.other = get_user_model().objects.create_user(username="money-other")

    def test_orm_api_numeric_rounding_and_partial_update(self):
        serializer = InvestmentSerializer(data={"asset_type": "cash", "asset_name": "Cash", "current_value": "2.675"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        row = serializer.save(user=self.user)
        row.refresh_from_db()
        self.assertEqual(row.current_value, Decimal("2.68"))
        self.assertIsInstance(InvestmentSerializer(row).data["current_value"], float)
        self.assertEqual(row.invested_amount, Decimal("0.00"))
        row.monthly_sip = "1.005"
        row.save()
        row.refresh_from_db()
        self.assertEqual(row.monthly_sip, Decimal("1.01"))
        for value in (None, True, "NaN", "1e100", -1):
            invalid = InvestmentSerializer(row, data={"current_value": value}, partial=True)
            self.assertFalse(invalid.is_valid())
        row.current_value = "NaN"
        with self.assertRaises(ValidationError):
            row.save()

    def test_owned_totals_above_stored_bound_and_decimal_mix(self):
        for name in ("One", "Two"):
            Investment.objects.create(user=self.user, asset_name=name, asset_type="equity", current_value="999999999999.99")
        Investment.objects.create(user=self.other, asset_name="Other", asset_type="cash", current_value=100)
        self.assertEqual(_investment_allocation_payload(self.user)["values"], [1999999999999.98])
        self.assertEqual(portfolio_intelligence_service._portfolio_mix(self.user)["equity_pct"], 100.0)
        risk = portfolio_intelligence_service.analyze_portfolio_risk(self.user)
        self.assertEqual(risk["total_portfolio_value"], 1999999999999.98)

    def test_risk_threshold_uses_exact_decimal_ratio(self):
        rows = [Investment(asset_type="equity", current_value=Decimal("65")), Investment(asset_type="cash", current_value=Decimal("35"))]
        self.assertEqual(_portfolio_risk(rows), "High")

    def test_retry_failure_rolls_back_prior_rows_and_zero_preservation(self):
        row = Investment.objects.create(user=self.user, asset_name="Keep", asset_type="cash", current_value=20)
        with self.assertRaises(ValueError):
            _upsert_retry_investments(self.user, [{"asset_name": "Keep", "current_value": "2.675"}, {"asset_name": "Invalid", "current_value": "NaN"}])
        row.refresh_from_db()
        self.assertEqual(row.current_value, 20)
        _upsert_retry_investments(self.user, [{"asset_name": "Keep", "current_value": 0}], preserve_existing=True)
        row.refresh_from_db()
        self.assertEqual(row.current_value, 20)
        _upsert_retry_investments(self.user, [{"asset_name": "Keep", "current_value": 0}], preserve_existing=True, primary_corrections={"current_value": 0})
        row.refresh_from_db()
        self.assertEqual(row.current_value, 0)

    def test_pdf_persistence_is_atomic_for_invalid_holdings(self):
        parsed = {"investments": [{"asset_name": "Valid", "current_value": "2.675"}, {"asset_name": "Invalid", "current_value": "Infinity"}]}
        with patch.object(portfolio_intelligence_service, "parse_portfolio_document", return_value=parsed):
            with self.assertRaises(ValueError):
                portfolio_intelligence_service.parse_portfolio_pdf(None, self.user)
        self.assertFalse(Investment.objects.filter(user=self.user).exists())

    def test_correction_json_preserves_raw_evidence_and_rejects_invalid_atomically(self):
        row = Investment.objects.create(user=self.user, asset_name="Holding", asset_type="cash", current_value=20)
        doc = InvestmentImportDocument.objects.create(user=self.user, file_name="proof.pdf", extracted_payload={"raw": "2.675 evidence"})
        doc.linked_investments.add(row)
        with patch("alfred_ai.services.document_review.record_parser_correction"):
            _apply_investment_correction(self.user, doc.pk, {"current_value": "2.675"})
        doc.refresh_from_db()
        self.assertEqual(doc.extracted_payload["raw"], "2.675 evidence")
        self.assertEqual(doc.extracted_payload["investments"][0]["current_value"], 2.68)
        before = doc.extracted_payload
        with self.assertRaises(ValueError):
            _apply_investment_correction(self.user, doc.pk, {"broker_name": "Changed", "current_value": "NaN"})
        doc.refresh_from_db()
        self.assertEqual(doc.extracted_payload, before)
        self.assertEqual(doc.broker_name, "")

    def test_owned_reset_removes_retained_orphan_evidence(self):
        snapshots = []
        for owner in (self.user, self.other):
            row = Investment.objects.create(user=owner, asset_name="Reset", asset_type="cash")
            snapshots.append(InvestmentMoneySnapshot.objects.create(
                user=owner, investment=row, original_investment_id=row.pk,
                source_values={"current_value": "2.675"}, normalized_values={"current_value": "2.68"},
            ))
            if owner == self.user:
                row.delete()
        snapshots[0].refresh_from_db()
        self.assertIsNone(snapshots[0].investment_id)
        summary = clear_user_fed_data(self.user)
        self.assertEqual(summary["investment_money_snapshots"], 1)
        self.assertFalse(InvestmentMoneySnapshot.objects.filter(user=self.user).exists())
        self.assertTrue(InvestmentMoneySnapshot.objects.filter(pk=snapshots[1].pk, user=self.other).exists())


class InvestmentMoneyMigrationTests(TransactionTestCase):
    migrate_from = ("investments", "0003_rename_investmenti_user_id_a9ad33_idx_investments_user_id_cbfa4c_idx_and_more")
    migrate_to = ("investments", "0004_investment_money_decimal")

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        executor.migrate([self.migrate_from])
        targets = [self.migrate_from if x[0] == "investments" else x for x in self.leaves]
        self.old = executor.loader.project_state(targets).apps
        self.user = self.old.get_model("users", "User").objects.create(username="migration-owner")

    def upgrade(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        targets = [self.migrate_to if x[0] == "investments" else x for x in self.leaves]
        return executor.loader.project_state(targets).apps

    def test_retained_evidence_repeat_apply_and_guarded_owned_rollback(self):
        Old = self.old.get_model("investments", "Investment")
        row = Old.objects.create(user_id=self.user.pk, asset_type="cash", asset_name="Legacy", invested_amount=2.675, monthly_sip=-1.005, current_value=0.005, annual_return_rate=8.123456789)
        apps = self.upgrade()
        New = apps.get_model("investments", "Investment")
        Snapshot = apps.get_model("investments", "InvestmentMoneySnapshot")
        updated = New.objects.get(pk=row.pk)
        self.assertEqual((updated.invested_amount, updated.monthly_sip, updated.current_value), (Decimal("2.68"), Decimal("-1.01"), Decimal("0.01")))
        self.assertEqual(updated.annual_return_rate, row.annual_return_rate)
        snapshot = Snapshot.objects.get(original_investment_id=row.pk)
        self.assertEqual(snapshot.source_values["invested_amount"], "2.675")
        self.assertIsNotNone(snapshot.applied_at)
        New.objects.filter(pk=row.pk).update(current_value=30)
        module = import_module("apps.investments.migrations.0004_investment_money_decimal")
        with connection.schema_editor() as editor:
            module.apply_normalized_money(apps, editor)
        self.assertEqual(New.objects.get(pk=row.pk).current_value, 30)
        MigrationExecutor(connection).migrate([self.migrate_from])
        restored = Old.objects.get(pk=row.pk)
        self.assertEqual(restored.invested_amount, row.invested_amount)
        self.assertEqual(restored.monthly_sip, row.monthly_sip)
        self.assertEqual(restored.current_value, 30)

    def test_invalid_legacy_amount_leaves_original_register_unchanged(self):
        Old = self.old.get_model("investments", "Investment")
        row = Old.objects.create(user_id=self.user.pk, asset_type="cash", asset_name="Invalid", current_value=1e20)
        with self.assertRaises(ValueError):
            self.upgrade()
        self.assertEqual(Old.objects.get(pk=row.pk).current_value, 1e20)
        # Remove only this synthetic invalid fixture so cleanup can restore latest schema.
        row.delete()

    def test_unapplied_or_changed_owner_snapshot_does_not_restore_old_values(self):
        Old = self.old.get_model("investments", "Investment")
        first = Old.objects.create(user_id=self.user.pk, asset_type="cash", asset_name="Marker", current_value=2.675)
        second = Old.objects.create(user_id=self.user.pk, asset_type="cash", asset_name="Owner", current_value=3.675)
        apps = self.upgrade()
        New = apps.get_model("investments", "Investment")
        Snapshot = apps.get_model("investments", "InvestmentMoneySnapshot")
        other = apps.get_model("users", "User").objects.create(username="new-owner")
        Snapshot.objects.filter(original_investment_id=first.pk).update(applied_at=None)
        New.objects.filter(pk=second.pk).update(user_id=other.pk)
        MigrationExecutor(connection).migrate([self.migrate_from])
        self.assertEqual(Old.objects.get(pk=first.pk).current_value, 2.68)
        self.assertEqual(Old.objects.get(pk=second.pk).current_value, 3.68)
        self.assertEqual(Old.objects.get(pk=second.pk).user_id, other.pk)
