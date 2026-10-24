"""Additive receipt migration/recovery rehearsal on a separate synthetic alias."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from scripts.rehearse_money_migrations import copy_database, file_hash, read_database, table_digest


class StatementEvidenceMigrationTests(TransactionTestCase):
    def test_forward_reverse_and_independent_restore_leave_financial_rows_unchanged(self):
        leaves=MigrationExecutor(connection).loader.graph.leaf_nodes()
        baseline=[('expenses','0005_expense_bank_money_decimal') if item[0]=='expenses' else item for item in leaves]
        with TemporaryDirectory(prefix='alfred-source-rehearsal-synthetic-') as directory:
            root=Path(directory); source, candidate, restored=[root/name for name in ('source.sqlite3','candidate.sqlite3','restore.sqlite3')]
            alias='statement_evidence_rehearsal'; db=connection.copy(alias=alias)
            db.settings_dict['NAME']=str(source); connections[alias]=db
            try:
                executor=MigrationExecutor(db); executor.migrate(baseline)
                apps=executor.loader.project_state(baseline).apps
                user=apps.get_model('users','User').objects.using(alias).create(username='source-rehearsal-owner',monthly_income='12345.67')
                other=apps.get_model('users','User').objects.using(alias).create(username='source-rehearsal-other')
                account=apps.get_model('expenses','BankAccount').objects.using(alias).create(user_id=user.pk,account_number='SYNTHETIC-ONLY',current_balance='10.01')
                document=apps.get_model('expenses','StatementUpload').objects.using(alias).create(user_id=user.pk,bank_account_id=account.pk,file_name='synthetic.pdf')
                expense=apps.get_model('expenses','Expense').objects.using(alias).create(user_id=user.pk,bank_account_id=account.pk,
                    statement_upload_id=document.pk,amount='2.68',closing_balance='10.01',transaction_date=date(2026,9,1),
                    transaction_fingerprint='f'*64,transaction_identity={'amount':'2.675','closing_balance':'10.005'})
                apps.get_model('family','FamilyAccountLink').objects.using(alias).create(created_by_id=user.pk,linked_user_id=other.pk,
                    status='accepted',invite_code_hash='e'*64,share_financial_summary=False,expires_at=timezone.now())
                db.close(); original_hash=file_hash(source); before=read_database(source)
                copy_database(source,candidate); copy_database(source,restored)
                self.assertEqual(read_database(restored),before)
                db.settings_dict['NAME']=str(candidate)
                executor=MigrationExecutor(db)
                plan=[(m.app_label,m.name,backwards) for m,backwards in executor.migration_plan(leaves)]
                self.assertEqual(plan,[('expenses','0006_statement_transaction_evidence',False)])
                executor.migrate(leaves); apps=executor.loader.project_state(leaves).apps
                Proof=apps.get_model('expenses','StatementTransactionEvidence')
                self.assertEqual(Proof.objects.using(alias).count(),0)
                Proof.objects.using(alias).create(expense_id=expense.pk,statement_upload_id=document.pk,source_values={'amount':'2.68'})
                db.close(); after,_=read_database(candidate)
                for name, rows in before[0].items():
                    if name!='django_migrations': self.assertEqual(table_digest(rows),table_digest(after[name]),name)
                MigrationExecutor(db).migrate(baseline); db.close()
                reverse,_=read_database(candidate)
                self.assertEqual({name:table_digest(rows) for name,rows in reverse.items()},
                    {name:table_digest(rows) for name,rows in before[0].items()})
                self.assertEqual(file_hash(source),original_hash)
            finally:
                db.close(); del connections[alias]
