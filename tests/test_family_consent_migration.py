"""Synthetic reconciliation and privacy-preserving rollback of M14G."""
from datetime import timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class FamilyConsentMigrationTests(TransactionTestCase):
    migrate_from = ("family", "0003_familyaccountlink_share_financial_summary")
    migrate_to = ("family", "0004_financial_sharing_opt_in")

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        self.old_targets = [self.migrate_from if node[0] == "family" else node for node in self.leaves]
        executor.migrate(self.old_targets)
        apps = executor.loader.project_state(self.old_targets).apps
        users = apps.get_model("users", "User")
        self.owner = users.objects.create(username="historical-owner")
        self.member = users.objects.create(username="historical-member")
        apps.get_model("family", "Dependent").objects.create(user_id=self.owner.pk, name="Synthetic child", age=7, relation="Child")
        self.old_link = apps.get_model("family", "FamilyAccountLink")
        for index, state in enumerate(("accepted", "pending", "revoked", "expired")):
            self.old_link.objects.create(created_by_id=self.owner.pk,
                linked_user_id=self.member.pk if state != "pending" else None,
                invite_code_hash=str(index) * 64, invite_code_hint="TEST", status=state,
                share_profile_summary=index % 2 == 0, share_dependents=index % 2 == 1,
                share_financial_summary=index != 3, expires_at=timezone.now() + timedelta(days=1))
        self.before = list(self.old_link.objects.order_by("pk").values())

    def upgrade(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan([self.migrate_to])
        self.assertEqual([(migration.app_label, migration.name, backwards) for migration, backwards in plan],
                         [("family", self.migrate_to[1], False)])
        executor.migrate(self.leaves)
        return executor.loader.project_state(self.leaves).apps

    def assert_relationships_preserved(self, model):
        after = list(model.objects.order_by("pk").values())
        self.assertEqual(len(after), 4)
        for old, new in zip(self.before, after):
            self.assertEqual({key: new[key] for key in old if key != "share_financial_summary"},
                             {key: value for key, value in old.items() if key != "share_financial_summary"})
            self.assertFalse(new["share_financial_summary"])

    def test_historical_true_defaults_are_disabled_with_all_relationships_preserved(self):
        apps = self.upgrade()
        model = apps.get_model("family", "FamilyAccountLink")
        self.assert_relationships_preserved(model)
        self.assertFalse(model.objects.filter(linked_user_share_financial_summary=True).exists())
        self.assertEqual(apps.get_model("users", "User").objects.count(), 2)
        self.assertEqual(apps.get_model("family", "Dependent").objects.count(), 1)
        from django.contrib.auth import get_user_model
        from apps.family.services import family_financial_user_ids
        self.assertEqual(family_financial_user_ids(get_user_model().objects.get(pk=self.owner.pk)), [self.owner.pk])
        self.assertEqual(family_financial_user_ids(get_user_model().objects.get(pk=self.member.pk)), [self.member.pk])
        self.assertEqual(model._meta.get_field("share_financial_summary").default, False)
        self.assertEqual(model._meta.get_field("linked_user_share_financial_summary").default, False)

    def test_rollback_and_replay_keep_permissions_off_and_preserve_records(self):
        model = self.upgrade().get_model("family", "FamilyAccountLink")
        model.objects.filter(status="accepted").update(share_financial_summary=True, linked_user_share_financial_summary=True)
        MigrationExecutor(connection).migrate(self.old_targets)
        self.assert_relationships_preserved(self.old_link)
        model = self.upgrade().get_model("family", "FamilyAccountLink")
        self.assert_relationships_preserved(model)
        self.assertFalse(model.objects.filter(linked_user_share_financial_summary=True).exists())
