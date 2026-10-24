"""Synthetic forward/reverse and backup recovery; no live database access."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone
from scripts.rehearse_money_migrations import copy_database, file_hash, read_database, table_digest


class LoanEvidenceMigrationTests(TransactionTestCase):
    def test_forward_empty_reverse_guard_and_restore_preserve_all_financial_rows(self):
        leaves=MigrationExecutor(connection).loader.graph.leaf_nodes()
        baseline=[('loans','0015_related_loan_money_decimal') if item[0]=='loans' else item for item in leaves]
        with TemporaryDirectory(prefix='alfred-loan-evidence-synthetic-') as directory:
            root=Path(directory); source,candidate,restored=[root/name for name in ('source.sqlite3','candidate.sqlite3','restore.sqlite3')]
            alias='loan_evidence_rehearsal'; db=connection.copy(alias=alias)
            db.settings_dict['NAME']=str(source); connections[alias]=db
            try:
                executor=MigrationExecutor(db); executor.migrate(baseline)
                apps=executor.loader.project_state(baseline).apps
                owner=apps.get_model('users','User').objects.using(alias).create(username='synthetic-rehearsal-owner',monthly_income='12345.67')
                other=apps.get_model('users','User').objects.using(alias).create(username='synthetic-rehearsal-other')
                account=apps.get_model('expenses','BankAccount').objects.using(alias).create(user_id=owner.pk,account_number='SYNTHETIC',current_balance='10.01')
                apps.get_model('expenses','Expense').objects.using(alias).create(user_id=owner.pk,bank_account_id=account.pk,
                    amount='2.68',transaction_date=date(2026,9,1),transaction_fingerprint='f'*64,transaction_identity={'amount':'2.675'})
                loan=apps.get_model('loans','Loan').objects.using(alias).create(user_id=owner.pk,principal='100.01',emi='1.01',
                    remaining_balance='98.99',interest_rate=5,start_date=date(2026,1,1))
                document=apps.get_model('loans','LoanImportDocument').objects.using(alias).create(user_id=owner.pk,file_name='synthetic.pdf')
                document.linked_loans.add(loan)
                apps.get_model('family','FamilyAccountLink').objects.using(alias).create(created_by_id=owner.pk,linked_user_id=other.pk,
                    status='accepted',invite_code_hash='e'*64,share_financial_summary=False,expires_at=timezone.now())
                db.close(); before=read_database(source); self.assertEqual(before[1],[]); original_hash=file_hash(source)
                copy_database(source,candidate); copy_database(source,restored)
                self.assertEqual(read_database(restored),before)
                db.settings_dict['NAME']=str(candidate)
                executor=MigrationExecutor(db)
                self.assertEqual([(m.app_label,m.name,backwards) for m,backwards in executor.migration_plan(leaves)],
                    [('loans','0016_loan_document_evidence',False)])
                executor.migrate(leaves); db.close()
                after,foreign_keys=read_database(candidate); self.assertEqual(foreign_keys,[])
                for table,rows in before[0].items():
                    if table!='django_migrations': self.assertEqual(table_digest(rows),table_digest(after[table]),table)
                MigrationExecutor(db).migrate(baseline); db.close()
                self.assertEqual(read_database(candidate),before)
                executor=MigrationExecutor(db); executor.migrate(leaves)
                Proof=executor.loader.project_state(leaves).apps.get_model('loans','LoanDocumentEvidence')
                self.assertEqual(Proof.objects.using(alias).count(),0)
                Proof.objects.using(alias).create(document_id=document.pk,loan_id=loan.pk,
                    original_loan_id=loan.pk,source_values={'emi':'1.0100'})
                with self.assertRaisesRegex(RuntimeError,'verified pre-migration backup'):
                    MigrationExecutor(db).migrate(baseline)
                db.close()
                self.assertEqual(len(read_database(candidate)[0]['loans_loandocumentevidence']),1)
                self.assertEqual(read_database(restored),before)
                self.assertEqual(file_hash(source),original_hash)
            finally:
                db.close(); del connections[alias]
