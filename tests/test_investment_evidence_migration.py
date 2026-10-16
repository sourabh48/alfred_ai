"""Forward, guarded rollback and independent restore on a disposable SQLite alias."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone
from scripts.rehearse_money_migrations import copy_database, file_hash, read_database, table_digest


class InvestmentEvidenceMigrationTests(TransactionTestCase):
    def test_forward_empty_reverse_guard_and_restore_preserve_all_financial_rows(self):
        leaves=MigrationExecutor(connection).loader.graph.leaf_nodes()
        baseline=[('investments','0004_investment_money_decimal') if item[0]=='investments' else item for item in leaves]
        with TemporaryDirectory(prefix='alfred-investment-evidence-synthetic-') as directory:
            root=Path(directory); source,candidate,restored=[root/name for name in ('source.sqlite3','candidate.sqlite3','restore.sqlite3')]
            alias='investment_evidence_rehearsal'; db=connection.copy(alias=alias)
            db.settings_dict['NAME']=str(source); connections[alias]=db
            try:
                executor=MigrationExecutor(db); executor.migrate(baseline)
                apps=executor.loader.project_state(baseline).apps
                owner=apps.get_model('users','User').objects.using(alias).create(username='synthetic-rehearsal-owner',monthly_income='12345.67')
                other=apps.get_model('users','User').objects.using(alias).create(username='synthetic-rehearsal-other')
                account=apps.get_model('expenses','BankAccount').objects.using(alias).create(user_id=owner.pk,account_number='SYNTHETIC',current_balance='10.01')
                apps.get_model('expenses','Expense').objects.using(alias).create(user_id=owner.pk,bank_account_id=account.pk,
                    amount='2.68',transaction_date=date(2026,9,1),transaction_fingerprint='f'*64,transaction_identity={'amount':'2.675'})
                holding=apps.get_model('investments','Investment').objects.using(alias).create(user_id=owner.pk,
                    asset_name='SYNTHETIC',asset_type='equity',invested_amount='100.01',current_value='123.45',monthly_sip='1.01')
                document=apps.get_model('investments','InvestmentImportDocument').objects.using(alias).create(user_id=owner.pk,file_name='synthetic.pdf')
                document.linked_investments.add(holding)
                apps.get_model('family','FamilyAccountLink').objects.using(alias).create(created_by_id=owner.pk,linked_user_id=other.pk,
                    status='accepted',invite_code_hash='e'*64,share_financial_summary=False,expires_at=timezone.now())
                db.close(); before=read_database(source); self.assertEqual(before[1],[]); original_hash=file_hash(source)
                copy_database(source,candidate); copy_database(source,restored)
                self.assertEqual(read_database(restored),before)
                db.settings_dict['NAME']=str(candidate)
                executor=MigrationExecutor(db)
                self.assertEqual([(m.app_label,m.name,backwards) for m,backwards in executor.migration_plan(leaves)],
                    [('investments','0005_investment_document_evidence',False)])
                executor.migrate(leaves); db.close()
                after,foreign_keys=read_database(candidate); self.assertEqual(foreign_keys,[])
                for table,rows in before[0].items():
                    if table!='django_migrations': self.assertEqual(table_digest(rows),table_digest(after[table]),table)
                MigrationExecutor(db).migrate(baseline); db.close()
                self.assertEqual(read_database(candidate),before)
                executor=MigrationExecutor(db); executor.migrate(leaves)
                Proof=executor.loader.project_state(leaves).apps.get_model('investments','InvestmentDocumentEvidence')
                self.assertEqual(Proof.objects.using(alias).count(),0)
                Proof.objects.using(alias).create(document_id=document.pk,investment_id=holding.pk,
                    original_investment_id=holding.pk,source_values={'current_value':'123.4500'})
                with self.assertRaisesRegex(RuntimeError,'verified pre-migration backup'):
                    MigrationExecutor(db).migrate(baseline)
                db.close()
                self.assertEqual(len(read_database(candidate)[0]['investments_investmentdocumentevidence']),1)
                self.assertEqual(read_database(restored),before)
                self.assertEqual(file_hash(source),original_hash)
            finally:
                db.close(); del connections[alias]
