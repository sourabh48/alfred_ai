"""integrations 0007 drops the credit score tables (FIN-17 OWNER_DESCOPED) but never loses a recorded card limit."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

BEFORE = ("integrations", "0006_verifiedexternalinsight_refresh_observability")
AFTER = ("integrations", "0007_drop_credit_score")
TABLES = {"integrations_creditscore", "integrations_creditscorefactor", "integrations_creditreportupload"}


class CreditScoreDropMigrationTests(TransactionTestCase):
    def setUp(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        executor = MigrationExecutor(connection)
        executor.migrate([BEFORE])
        # Every other app stays at its latest state; only integrations steps back.
        apps = executor.loader.project_state([BEFORE if node[0] == "integrations" else node for node in leaves]).apps
        self.Score = apps.get_model("integrations", "CreditScore")
        user = apps.get_model("users", "User").objects.create(username="synthetic-credit-owner")
        self.score = lambda limit: self.Score.objects.create(user_id=user.pk, bureau="cibil", score=700, rating="Good",
                                                             valid_until=timezone.now(), total_credit_limit=limit)

    def tables(self):
        return TABLES & set(connection.introspection.table_names())

    def test_drop_removes_the_three_tables(self):
        self.score(0)
        MigrationExecutor(connection).migrate([AFTER])
        self.assertEqual(self.tables(), set())

    def test_a_recorded_card_limit_stops_the_drop_and_keeps_every_row(self):
        self.score(0)
        self.score(150000.5)
        with self.assertRaisesRegex(RuntimeError, "1 credit score row"):
            MigrationExecutor(connection).migrate([AFTER])
        self.assertEqual(self.tables(), TABLES)
        self.assertEqual(sorted(self.Score.objects.values_list("total_credit_limit", flat=True)), [0, 150000.5])
        self.addCleanup(self.Score.objects.all().delete)  # runs first, so the cleanup migration can drop the tables
