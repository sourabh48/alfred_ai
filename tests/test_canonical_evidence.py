"""Synthetic canonical records; no production database, model or provider requests."""
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import TestCase, Client, override_settings

from apps.budgets.models import Budget
from apps.expenses.models import BankAccount, Expense, StatementUpload, StatementTransactionEvidence
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.expenses.services.statement_evidence import evidence, review
from apps.expenses.services.statement_lifecycle import _import_statement_transactions
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanPaymentHistory
from apps.ml_engine.services.canonical_evidence import record_source, choices, baseline_source, supported_question
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_expense_money_identity import parsed_fixture


class CanonicalEvidenceTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-canonical-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=self.root/'media',ALFRED_MEMORY_DIR=str(self.root/'unused-vault'),
            ALFRED_ABUSE_THROTTLE_DIR=str(self.root/'limits'),ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,
            ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALFRED_MEMORY_SYNC_PROVIDER=''))
        self.enterContext(_offline_fixture_patches())
        self.owner=get_user_model().objects.create_user(username='canonical-owner',monthly_income='12345.67',rent_or_emi='123.45')
        self.other=get_user_model().objects.create_user(username='canonical-other')
        self.account=BankAccount.objects.create(user=self.owner,account_number='SYNTHETIC-ACCOUNT-ONLY',current_balance='987.65')
        self.expense=Expense.objects.create(user=self.owner,bank_account=self.account,amount='12.34',
            transaction_date=date(2026,9,1),source='manual',category='food',raw_description='SYNTHETIC-NO-MODEL-CONTEXT')
        self.budget=Budget.objects.create(user=self.owner,month='Sep 2026',base_budget='123.45',inflation_adjusted='134.56',spent='12.34')
        self.loan=Loan.objects.create(user=self.owner,principal='10000.01',emi='100.01',remaining_balance='9000.01',
            interest_rate=5,tenure_months=100,start_date=date(2026,1,1),verification_status='confirmed')
        self.investment=Investment.objects.create(user=self.owner,asset_type='equity',asset_name='SYNTHETIC-NAME-NOT-PROMPT',
            invested_amount='2000.01',current_value='2345.67',monthly_sip='123.45',account_number='SYNTHETIC-NO-EXTERNAL')
        self.rows={'expense':self.expense,'budget':self.budget,'loan':self.loan,'investment':self.investment,'baseline':self.owner}
        self.client.force_login(self.owner)

    def url(self, kind):
        return f'/api/ai/financial-evidence/{kind}/{self.rows[kind].pk}/'

    def test_owned_exact_records_provenance_dates_revision_and_unknown_currency(self):
        expected={'expense':('amount','12.34'),'budget':('base_budget','123.45'),
            'loan':('emi','100.01'),'investment':('current_value','2345.67'),'baseline':('monthly_income','12345.67')}
        for kind,(field,value) in expected.items():
            with self.subTest(kind=kind):
                result=record_source(self.owner,kind,self.rows[kind].pk)
                self.assertTrue(result['available']); self.assertEqual(result['record_type'],kind)
                money=result['data']['amounts'][field]
                self.assertEqual(money['amount'],value); self.assertIsNone(money['currency'])
                self.assertEqual(money['currency_status'],'not_recorded')
                self.assertEqual(money['record_id'],self.rows[kind].pk)
                self.assertEqual(money['revision'],result['revision']); self.assertEqual(len(result['revision']),64)
                self.assertTrue(money['provenance']); self.assertTrue(money['as_of'])
                response=self.client.get(self.url(kind)); self.assertEqual(response.status_code,200)
                self.assertIn('no-store',response['Cache-Control'])
                self.assertEqual(self.client.get(result['url']).status_code,200)

    def test_owner_isolation_including_citations_and_accepted_family_sharing(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.family.models import FamilyAccountLink
        FamilyAccountLink.objects.create(created_by=self.owner,linked_user=self.other,status='accepted',invite_code_hash='b'*64,
            expires_at=timezone.now()+timedelta(days=1),share_financial_summary=True,linked_user_share_financial_summary=True)
        for actor in (None,self.other):
            client=Client()
            if actor: client.force_login(actor)
            for kind,row in self.rows.items():
                with self.subTest(actor=bool(actor),kind=kind):
                    source=record_source(self.owner,kind,row.pk)
                    self.assertIn(client.get(self.url(kind)).status_code,(401,403,404))
                    self.assertIn(client.get(source['url']).status_code,(302,404))
        self.assertEqual([x['kind'] for x in choices(self.other)],['baseline'])
        self.client.logout(); self.client.cookies['sessionid']='invalid-synthetic-session'
        self.assertIn(self.client.get(self.url('loan')).status_code,(401,403))

    def test_corrections_precede_extraction_and_snapshots_are_untouched(self):
        original=list(Expense.objects.values())
        before=record_source(self.owner,'expense',self.expense.pk)['revision']
        Expense.objects.filter(pk=self.expense.pk).update(amount='56.78')
        source=record_source(self.owner,'expense',self.expense.pk)
        self.assertEqual(source['data']['amounts']['amount']['amount'],'56.78')
        self.assertNotEqual(source['revision'],before)
        document=InvestmentImportDocument.objects.create(user=self.owner,file_name='synthetic-original.pdf',
            extracted_payload={'current_value':'1.23','raw_text':'SYNTHETIC-OCR-NOT-USED'},parser_status='parsed')
        document.linked_investments.add(self.investment)
        source=record_source(self.owner,'investment',self.investment.pk)
        self.assertEqual(source['data']['amounts']['current_value']['amount'],'2345.67')
        self.assertEqual(source['data']['verification'],'imported_record_not_field_verified')
        document.refresh_from_db(); self.assertEqual(document.extracted_payload['current_value'],'1.23')
        self.assertEqual(Expense.objects.get(pk=self.expense.pk).transaction_fingerprint,original[0]['transaction_fingerprint'])

    def test_budget_approval_is_not_invented_and_conflicting_alias_periods_abstain(self):
        source=record_source(self.owner,'budget',self.budget.pk)
        self.assertEqual(source['data']['verification'],'owner_saved_approval_not_recorded')
        Budget.objects.create(user=self.owner,month='2026-09',base_budget='999.99',inflation_adjusted='999.99',spent='0.00')
        source=record_source(self.owner,'budget',self.budget.pk)
        self.assertFalse(source['available']); self.assertEqual(source['data']['verification'],'conflicting_budget_records')
        self.assertTrue(all(value['amount'] is None for value in source['data']['amounts'].values()))

    def test_loans_use_contract_emi_and_recorded_payments_not_new_calculations(self):
        payment=LoanPaymentHistory.objects.create(loan=self.loan,payment_date=date(2026,9,1),amount='100.01',
            remaining_balance='9000.01',match_status='matched',loan_effect_applied=True,expense_reference=self.expense)
        source=record_source(self.owner,'loan',self.loan.pk)
        self.assertEqual(source['data']['amounts']['emi']['amount'],'100.01')
        self.assertEqual(source['data']['last_applied_payment_id'],payment.pk)
        Loan.objects.filter(pk=self.loan.pk).update(remaining_balance=None)
        source=record_source(self.owner,'loan',self.loan.pk)
        self.assertIsNone(source['data']['amounts']['remaining_balance']['amount'])
        self.assertEqual(source['data']['amounts']['remaining_balance']['evidence_status'],'unavailable')
        Loan.objects.filter(pk=self.loan.pk).update(status='closed',remaining_balance='9.99')
        self.assertFalse(record_source(self.owner,'loan',self.loan.pk)['available'])
        Loan.objects.filter(pk=self.loan.pk).update(status='active',verification_status='estimated')
        self.assertFalse(record_source(self.owner,'loan',self.loan.pk)['available'])

    def test_conflicting_closure_and_foreign_parent_linkage_are_rejected(self):
        for amount in ('0.00','1.00'):
            LoanClosureDocument.objects.create(loan=self.loan,verification_status='verified',closure_amount=amount)
        self.assertFalse(record_source(self.owner,'loan',self.loan.pk)['available'])
        foreign=BankAccount.objects.create(user=self.other,account_number='SYNTHETIC-FOREIGN')
        Expense.objects.filter(pk=self.expense.pk).update(bank_account=foreign)
        with self.assertRaises(Http404): record_source(self.owner,'expense',self.expense.pk)
        document=InvestmentImportDocument.objects.create(user=self.other,file_name='foreign.pdf')
        document.linked_investments.add(self.investment)
        with self.assertRaises(Http404): record_source(self.owner,'investment',self.investment.pk)

    def test_applied_payment_awaiting_review_is_conflicting_not_verified_repayment(self):
        LoanPaymentHistory.objects.create(loan=self.loan,payment_date=date(2026,9,1),amount='100.01',
            match_status='review',loan_effect_applied=True,expense_reference=self.expense)
        result=record_source(self.owner,'loan',self.loan.pk)
        self.assertFalse(result['available']); self.assertEqual(result['data']['verification'],'conflicting_loan_records')
        self.assertEqual(result['data']['missed_payments'],0)

    def test_payment_source_revision_and_import_owner_boundary(self):
        from apps.loans.models import LoanImportDocument
        LoanPaymentHistory.objects.create(loan=self.loan,payment_date=date(2026,9,1),amount='100.01',
            match_status='matched',loan_effect_applied=True,expense_reference=self.expense)
        before=record_source(self.owner,'loan',self.loan.pk)['revision']
        Expense.objects.filter(pk=self.expense.pk).update(amount='23.45')
        self.assertNotEqual(record_source(self.owner,'loan',self.loan.pk)['revision'],before)
        document=LoanImportDocument.objects.create(user=self.other,file_name='synthetic-foreign.pdf')
        document.linked_loans.add(self.loan)
        with self.assertRaises(Http404): record_source(self.owner,'loan',self.loan.pk)

    def test_baseline_totals_withheld_without_currency_and_uncached_user_reload(self):
        source=baseline_source(self.owner)
        for field in ('liquid_cash','recurring_emi_burden','total_assets','total_liabilities','net_worth'):
            self.assertIsNone(source['data'][field]); self.assertIsNone(source['data']['amounts'][field]['amount'])
        self.assertNotIn('987.65',json.dumps(source))
        get_user_model().objects.filter(pk=self.owner.pk).update(monthly_income='23456.78')
        source=baseline_source(self.owner)
        self.assertEqual(source['data']['amounts']['monthly_income']['amount'],'23456.78')
        current=get_user_model().objects.get(pk=self.owner.pk)
        baseline=resolve_canonical_financial_baseline(current,fresh=True)
        self.assertEqual(source['data']['amounts']['monthly_income']['amount'],baseline['decimal_amounts']['monthly_income'])

    def test_career_fallback_does_not_become_an_explicitly_reported_user_income_fact(self):
        from apps.career.models import CareerProfile
        get_user_model().objects.filter(pk=self.owner.pk).update(monthly_income='0.00')
        CareerProfile.objects.create(user=self.owner,role='Synthetic role',experience_years=1,skills='Synthetic',last_salary='10000.00')
        current=get_user_model().objects.get(pk=self.owner.pk)
        baseline=resolve_canonical_financial_baseline(current,fresh=True)
        self.assertEqual(baseline['income_source'],'reported_monthly_income')
        self.assertEqual(baseline['decimal_amounts']['monthly_income'],'10000.00')
        source=baseline_source(self.owner)
        self.assertIsNone(source['data']['amounts']['monthly_income']['amount'])
        self.assertEqual(source['data']['amounts']['monthly_income']['evidence_status'],'unavailable')

    def test_bank_record_selector_cannot_bypass_receipt_review(self):
        upload=StatementUpload.objects.create(user=self.owner,bank_account=self.account,account_number=self.account.account_number,
            original_file=SimpleUploadedFile('synthetic.pdf',b'%PDF-synthetic-canonical-only'),file_name='synthetic.pdf',parser_status='parsed')
        _import_statement_transactions(user=self.owner,upload=upload,bank_account=self.account,parsed=parsed_fixture())
        row=Expense.objects.get(statement_upload=upload)
        self.assertFalse(record_source(self.owner,'expense',row.pk)['available'])
        current=evidence(self.owner,row.pk); review(self.owner,row.pk,revision=current['revision'],confirm=True)
        self.assertTrue(record_source(self.owner,'expense',row.pk)['available'])
        current=evidence(self.owner,row.pk); review(self.owner,row.pk,revision=current['revision'],confirm=True,revoke=True)
        self.assertFalse(record_source(self.owner,'expense',row.pk)['available'])

    def test_invalid_missing_deleted_and_mutation_requests_are_rejected(self):
        for kind,identity in (('unknown',1),('loan',True),('loan',0),('loan',999999),('baseline',self.other.pk)):
            with self.assertRaises(Http404): record_source(self.owner,kind,identity)
        self.assertEqual(self.client.post(self.url('budget'),{'base_budget':'0.00'}).status_code,405)
        url=self.url('investment'); self.investment.delete()
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.client.get(f'/ai/financial-records/investment/{self.rows["investment"].pk or 0}/').status_code,404)

    def test_readonly_retrieval_preserves_financial_rows_and_canonical_decimal_baseline(self):
        models=(Expense,BankAccount,Budget,Loan,LoanPaymentHistory,Investment,get_user_model(),StatementUpload,StatementTransactionEvidence)
        before=[list(model.objects.order_by('pk').values()) for model in models]
        baseline=resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts']
        for kind,row in self.rows.items():
            self.assertEqual(self.client.get(self.url(kind)).status_code,200)
            self.assertEqual(self.client.get(record_source(self.owner,kind,row.pk)['url']).status_code,200)
        self.assertEqual([list(model.objects.order_by('pk').values()) for model in models],before)
        self.assertEqual(resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts'],baseline)
        self.assertFalse(Path(settings.ALFRED_MEMORY_DIR).exists())

    def test_supported_questions_fail_closed_for_forecasts_currency_and_unrelated_topics(self):
        for query in ('Explain this record','Show my loan status','Review recorded values','Explain this evidence and limitations'):
            self.assertTrue(supported_question(query),query)
        for query in ('What is the weather?','Convert my balance to INR','Show total records','Predict investment prices',
                      'Approve my budget','Explain future loan','Write a cheque'):
            self.assertFalse(supported_question(query),query)

    def test_record_question_subjects_match_only_the_selected_canonical_domain(self):
        subjects={'expense':('expense','transaction'),'budget':('budget',),'loan':('loan','EMI','repayment status'),
            'investment':('investment',),'baseline':('baseline','income','rent')}
        for kind in subjects:
            for owner,nouns in subjects.items():
                for noun in nouns:
                    self.assertEqual(supported_question(f'Show my {noun}',kind=kind),owner==kind)
            for noun in ('record','records','values','evidence','provenance'):
                self.assertTrue(supported_question(f'Explain this {noun}',kind=kind))
        self.assertFalse(supported_question('Explain this record',kind='unsupported'))
