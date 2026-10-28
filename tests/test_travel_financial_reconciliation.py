"""Cross-module, isolated reconciliation receipts for C1→C2→C3."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from alfred_private_storage import private_directory

from django.contrib.auth import get_user_model
from django.apps import apps
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.expenses.models import BankAccount, Expense, StatementUpload, StatementTransactionEvidence
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.expenses.services.statement_evidence import evidence, review
from apps.expenses.services.statement_lifecycle import _import_statement_transactions
from apps.loans.models import Loan, LoanPaymentHistory
from apps.mobility.models import TravelPlan, TravelPlanningSession
from apps.mobility.services.travel.affordability import affordability_source, calculate_affordability
from apps.mobility.services.travel.savings import calculate_savings
from tests import test_travel_savings as fixtures
from tests.test_expense_money_identity import parsed_fixture
from scripts.release_validation import environment


class TravelFinancialReconciliationTests(TestCase):
    def setUp(self):
        fixtures.TravelSavingsTests.setUp(self)
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-travel-reconcile-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=private_directory(root/'media')))
        self.enterContext(patch('apps.expenses.services.transaction_intelligence.alfred_engine.predict_emotional_spend',
                                return_value={'confidence':.1,'is_emotional':False}))
        self.account.account_number='TEST0001';self.account.save()
        self.upload=StatementUpload.objects.create(user=self.user,bank_account=self.account,account_number='TEST0001',
            file_name='synthetic.pdf',parser_status='parsed',statement_start=date(2028,1,1),statement_end=date(2028,1,31),
            original_file=SimpleUploadedFile('synthetic.pdf',b'%PDF synthetic reconciliation source'),
            extracted_payload={'raw_text_excerpt':'SYNTHETIC PRIVATE SOURCE'})
        self.parsed=parsed_fixture(amount=Decimal('25'),closing=Decimal('1000'),category='loan')
        self.parsed.transactions[0].transaction_date=date(2028,1,30)
        self.parsed.transactions[0].classification='loan'
        self.parsed.statement_start=date(2028,1,1);self.parsed.statement_end=date(2028,1,31)
        rows,skipped=self.import_rows(self.parsed)
        self.assertEqual((len(rows),skipped),(1,0));self.payment=Expense.objects.get(statement_upload=self.upload)
        self.confirm_source(self.payment)
        LoanPaymentHistory.objects.create(loan=self.loan,payment_date=date(2028,1,30),amount='25',
            principal_paid='20',interest_paid='5',remaining_balance='800',match_status='matched',
            loan_effect_applied=True,expense_reference=self.payment)

    confirmation=fixtures.TravelSavingsTests.confirmation
    assumptions=fixtures.TravelSavingsTests.assumptions
    payload=fixtures.TravelSavingsTests.payload
    post=fixtures.TravelSavingsTests.post

    def import_rows(self, parsed, account=None, upload=None):
        return _import_statement_transactions(user=self.user,upload=upload or self.upload,
                                              bank_account=account or self.account,parsed=parsed)

    def confirm_source(self, row):
        review(self.user,row.pk,revision=evidence(self.user,row.pk)['revision'],confirm=True)

    def c2(self,payload=None):
        data=deepcopy(payload or self.payload());data.pop('savings')
        return self.client.post(self.url.replace('/savings/','/affordability/'),data,content_type='application/json')

    def snapshot(self):
        models=[model for label in ('users','expenses','loans','budgets','investments','career')
                for model in apps.get_app_config(label).get_models()]+[TravelPlan,TravelPlanningSession]
        return {model._meta.label:deepcopy(list(model.objects.order_by('pk').values())) for model in models}

    def test_import_transfer_and_repayment_identity_reconcile_all_three_layers(self):
        second=BankAccount.objects.create(user=self.user,account_number='TEST0002',current_balance='0',last_synced_at=timezone.now())
        other_upload=StatementUpload.objects.create(user=self.user,bank_account=second,account_number='TEST0002',
            parser_status='parsed',original_file=SimpleUploadedFile('second.pdf',b'%PDF synthetic transfer'),file_name='second.pdf')
        for direction,account,upload in (('debit',self.account,self.upload),('credit',second,other_upload)):
            parsed=parsed_fixture(amount=Decimal('50'),closing=Decimal('0'),direction=direction,category='transfer',
                                  reference='SYNTHETIC-TRANSFER',account=account.account_number)
            parsed.transactions[0].transaction_date=date(2028,1,30)
            rows,skipped=self.import_rows(parsed,account,upload);self.assertEqual((len(rows),skipped),(1,0))
            self.confirm_source(Expense.objects.get(bank_account=account,external_reference='SYNTHETIC-TRANSFER'))
        before=self.snapshot()
        rows,skipped=self.import_rows(self.parsed);self.assertEqual((len(rows),skipped),(0,1))
        self.assertEqual(before,self.snapshot())
        baseline=resolve_canonical_financial_baseline(self.user,fresh=True)
        source=affordability_source(self.user)
        self.assertEqual(source['amounts'],dict(cash_limit='1000.00',essential_expenses='150.00',loan_obligations='25.00'))
        self.assertEqual(baseline['decimal_amounts']['essential_monthly_outflow'],'175.00')
        confirmation=self.confirmation();current=calculate_affordability(self.user,confirmation)
        c2=self.c2().json();c3=self.post(self.payload()).json()
        self.assertEqual(current['amounts'],c2['amounts']);self.assertEqual(current['amounts'],c3['current']['amounts'])
        self.assertEqual(current['amounts']['available_trip_funds'],'525.00')
        self.assertEqual(c3['starting_unallocated_cash'],'700.00')
        self.assertEqual(c3['scenarios']['baseline']['projected_trip_funds'],'1020.00')
        self.assertEqual([r['emi'] for r in c3['scenarios']['baseline']['months']],['25.00','25.00'])
        self.assertEqual(before,self.snapshot())

    def test_parser_and_original_file_changes_invalidate_dependent_results(self):
        payload=self.payload();old=evidence(self.user,self.payment.pk)['revision']
        StatementUpload.objects.filter(pk=self.upload.pk).update(parser_status='needs_review')
        self.assertNotEqual(old,evidence(self.user,self.payment.pk)['revision'])
        self.assertEqual(self.c2(payload).status_code,409)
        self.assertEqual(self.post(payload).status_code,409)
        StatementUpload.objects.filter(pk=self.upload.pk).update(parser_status='parsed')
        self.confirm_source(self.payment);payload=self.payload()
        Path(self.upload.original_file.path).write_bytes(b'%PDF changed synthetic source')
        self.assertEqual(self.c2(payload).status_code,409)
        self.assertEqual(self.post(payload).status_code,409)
        result=self.post(self.payload()).json()
        self.assertIsNone(result['scenarios']);self.assertEqual(result['status'],'INSUFFICIENT_DATA')

    def test_source_revocation_and_reparenting_cannot_be_reconfirmed_as_complete(self):
        payload=self.payload();detail=evidence(self.user,self.payment.pk)
        review(self.user,self.payment.pk,revision=detail['revision'],confirm=True,revoke=True)
        self.assertEqual(self.post(payload).status_code,409)
        self.assertIsNone(self.post(self.payload()).json()['scenarios'])
        StatementUpload.objects.filter(pk=self.upload.pk).update(user=self.other)
        self.assertIsNone(self.post(self.payload()).json()['scenarios'])

    def test_same_file_is_read_once_per_fresh_source_and_missing_source_abstains(self):
        from apps.expenses.services import statement_evidence as service
        parsed=deepcopy(self.parsed);parsed.transactions[0].external_reference='SYNTHETIC-SECOND'
        parsed.transactions[0].raw_description='SYNTHETIC SECOND PAYMENT'
        self.import_rows(parsed)
        row=Expense.objects.get(external_reference='SYNTHETIC-SECOND');self.confirm_source(row)
        with patch.object(service,'file_reference',wraps=service.file_reference) as reads:
            self.assertTrue(affordability_source(self.user)['complete'])
            self.assertEqual(reads.call_count,1)
        Path(self.upload.original_file.path).unlink()
        self.assertIn('UNVERIFIED_STATEMENT_SOURCE',affordability_source(self.user)['issues'])

    def test_statement_history_validation_has_bounded_query_count(self):
        with CaptureQueriesContext(connection) as initial:
            self.assertTrue(affordability_source(self.user)['complete'])
        for index in range(20):
            row=Expense.objects.create(user=self.user,bank_account=self.account,statement_upload=self.upload,
                source='bank_statement',amount='25',classification='loan',category='loan',transaction_date=date(2028,1,30),
                external_reference=f'SYNTHETIC-BATCH-{index}',transaction_fingerprint=f'synthetic-{index}')
            self.confirm_source(row)
        with CaptureQueriesContext(connection) as larger:
            self.assertTrue(affordability_source(self.user)['complete'])
        self.assertLessEqual(len(larger),len(initial)+1)

    def test_batched_evidence_matches_single_row_conflict_and_duplicate_guards(self):
        from apps.expenses.services.statement_evidence import evidence_for_rows
        duplicate=Expense.objects.create(user=self.user,bank_account=self.account,statement_upload=self.upload,
            source='bank_statement',amount=self.payment.amount,category='loan',classification='loan',
            transaction_date=self.payment.transaction_date,transaction_fingerprint=self.payment.transaction_fingerprint)
        rows=list(Expense.objects.select_related('bank_account','statement_upload__bank_account').filter(user=self.user))
        for identity,revision,status in evidence_for_rows(self.user,rows):
            single=evidence(self.user,identity)
            self.assertEqual((revision,status),(single['revision'],single['verification']))
        duplicate.transaction_fingerprint='different';duplicate.external_reference=self.payment.external_reference
        duplicate.raw_description=self.payment.raw_description;duplicate.amount='26';duplicate.save()
        rows=list(Expense.objects.select_related('bank_account','statement_upload__bank_account').filter(user=self.user))
        for identity,revision,status in evidence_for_rows(self.user,rows):
            single=evidence(self.user,identity)
            self.assertEqual((revision,status),(single['revision'],single['verification']))
        self.assertIn('UNVERIFIED_STATEMENT_SOURCE',affordability_source(self.user)['issues'])

    def test_every_canonical_record_history_and_fingerprint_stays_readonly(self):
        payload=self.payload();before=self.snapshot()
        before_hash=hashlib.sha256(json.dumps(before,sort_keys=True,default=str).encode()).hexdigest()
        def readonly(execute,sql,params,many,context):
            if not sql.lstrip().upper().startswith('UPDATE "DJANGO_SESSION"'):
                self.assertNotRegex(sql.lstrip().upper(),r'^(INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP)\b')
            return execute(sql,params,many,context)
        with connection.execute_wrapper(readonly),patch('requests.sessions.Session.request',side_effect=AssertionError('external request')):
            for _ in range(2):
                self.assertEqual(self.c2(payload).status_code,200)
                self.assertEqual(self.post(payload).status_code,200)
        self.assertEqual(before,self.snapshot())
        self.assertEqual(before_hash,hashlib.sha256(json.dumps(self.snapshot(),sort_keys=True,default=str).encode()).hexdigest())

    def test_date_expiry_and_saved_trip_change_preserve_unrelated_metadata(self):
        self.plan.planning_state={'packing':{'items':[{'id':'synthetic','checked':True}]},'reminders':{'enabled':False},
                                  'documents':[{'id':'synthetic-private'}]};self.plan.save()
        before=deepcopy(self.plan.planning_state);payload=self.payload()
        with patch('django.utils.timezone.localdate',return_value=date(2028,1,31)):
            self.assertEqual(self.post(payload).status_code,409)
        TravelPlan.objects.filter(pk=self.plan.pk).update(budget='999')
        self.assertEqual(self.c2(payload).status_code,409);self.assertEqual(self.post(payload).status_code,409)
        self.plan.refresh_from_db();self.assertEqual(before,self.plan.planning_state)

    def test_null_zero_investment_credit_and_disjoint_allocations_remain_distinct(self):
        BankAccount.objects.create(user=self.user,account_number='synthetic-investment',account_type='investment',current_balance='9000')
        self.assertEqual(affordability_source(self.user)['amounts']['cash_limit'],'1000.00')
        BankAccount.objects.filter(pk=self.account.pk).update(current_balance=None)
        self.assertFalse(affordability_source(self.user)['complete'])
        BankAccount.objects.filter(pk=self.account.pk).update(current_balance='0')
        c=self.confirmation();c['spendable_cash']['amount']='0'
        result=calculate_affordability(self.user,c);self.assertEqual(result['amounts']['shortfall'],'900.00')
        c['disjoint_allocations']=False;self.assertIsNone(calculate_affordability(self.user,c)['amounts'])

    def test_fresh_process_restart_reopens_saved_synthetic_sources_without_financial_writes(self):
        # Serialize only Django's isolated test database, never the operator database.
        self.assertTrue(connection.in_atomic_block)
        name=str(connection.settings_dict['NAME'])
        self.assertTrue(name.startswith('file:memorydb_') or Path(name).name.startswith('test_'))
        with TemporaryDirectory(prefix='alfred-travel-finance-restart-synthetic-') as folder:
            root=private_directory(Path(folder)/'runtime');database=root/'synthetic.sqlite3'
            database.write_bytes(connection.connection.serialize())
            payload=self.payload();(root/'input.json').write_text(json.dumps(payload),encoding='utf-8')
            env=environment(root/'child-runtime');env.update(DATABASE_URL='sqlite:///'+database.as_posix(),
                ALFRED_MEDIA_ROOT=str(settings.MEDIA_ROOT),ALFRED_LOCAL_ENV_FILE=str(root/'absent.env'),
                DJANGO_SECRET_KEY=settings.SECRET_KEY,
                DJANGO_SETTINGS_MODULE='alfred_ai.settings',SYNTHETIC_REOPEN=str(root),
                SYNTHETIC_OWNER=str(self.user.pk),SYNTHETIC_SESSION=str(self.session.pk))
            program='''
import hashlib,json,os
from datetime import date,datetime,timezone
from pathlib import Path
from unittest.mock import patch
import django
django.setup()
from django.contrib.auth import get_user_model
from django.db import connection
from apps.mobility.models import TravelPlanningSession
from apps.mobility.services.travel.affordability import calculate_affordability
from apps.mobility.services.travel.affordability_ui import affordability_scenario,trip_context
from apps.mobility.services.travel.savings import calculate_savings
root=Path(os.environ['SYNTHETIC_REOPEN']).resolve()
assert Path(connection.settings_dict['NAME']).resolve()==root/'synthetic.sqlite3'
data=json.loads((root/'input.json').read_text(encoding='utf-8'))
def readonly(execute,sql,params,many,context):
    assert not sql.lstrip().upper().startswith(('INSERT ','UPDATE ','DELETE ','REPLACE ','CREATE ','ALTER ','DROP '))
    return execute(sql,params,many,context)
with connection.execute_wrapper(readonly),patch('django.utils.timezone.localdate',return_value=date(2028,1,30)),patch('django.utils.timezone.now',return_value=datetime(2028,1,30,12,tzinfo=timezone.utc)),patch('requests.sessions.Session.request',side_effect=AssertionError('external request')):
    user=get_user_model().objects.get(pk=os.environ['SYNTHETIC_OWNER'])
    session=TravelPlanningSession.objects.select_related('plan').get(pk=os.environ['SYNTHETIC_SESSION'],user=user)
    assert trip_context(session,session.plan)['snapshot']==data['snapshot']
    c1=calculate_affordability(user,data['confirmation'])
    c2=affordability_scenario(user,data['confirmation'])
    c3=calculate_savings(user,data['confirmation'],data['savings'])
    assert c1['amounts']==c2['amounts']==c3['current']['amounts'] and c3['scenarios']
    print(json.dumps(c3,sort_keys=True))
'''
            before=hashlib.sha256(database.read_bytes()).hexdigest()
            expected=calculate_savings(self.user,payload['confirmation'],payload['savings'])
            for _ in range(2):
                process=subprocess.run([sys.executable,'-c',program],env=env,capture_output=True,text=True,timeout=60)
                self.assertEqual(process.returncode,0,process.stderr[-1200:])
                self.assertEqual(json.loads(process.stdout),expected)
                self.assertEqual(before,hashlib.sha256(database.read_bytes()).hexdigest())
