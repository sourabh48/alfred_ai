"""Synthetic monetary presentation; model prose never supplies financial figures."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from apps.loans.models import Loan, LoanClosureDocument
from apps.ml_engine.services.persistent_memory import MemoryStore
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
from tests.test_persistent_memory import SyntheticEmbeddings


class IntelligenceCurrencyTests(TestCase):
    def setUp(self):
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-currency-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.user=get_user_model().objects.create_user(username='synthetic-currency-owner')
        self.store=MemoryStore(root/'vault'); self.local=Mock()
        self.loan=Loan.objects.create(user=self.user,loan_type='personal',lender='Synthetic currency lender',principal=100,
            remaining_balance=0,interest_rate=5,emi=10,tenure_months=10,start_date=date(2026,1,1))
        self.document=LoanClosureDocument.objects.create(loan=self.loan,file_name='synthetic.pdf',closure_amount=Decimal('999999999999.99'),
            closure_date=date(2026,1,2),verification_status='verified')

    def answer(self,scope='documents',**kwargs):
        return hybrid_answer(self.store,self.user,'Explain my recorded facts',scope=scope,
            document_id=self.document.pk if scope=='documents' else None,local=self.local,**kwargs)

    def test_contradictory_currency_narrative_is_suppressed_and_record_cents_preserved(self):
        self.local.reason.return_value='The loan cost $12.00 USD.'
        result=self.answer()
        self.assertNotIn('$12.00',result['answer'])
        self.assertTrue(result['narrative_withheld'])
        amount=result['sources'][0]['data']['amounts']['closure_amount']
        self.assertEqual(amount['amount'],'999999999999.99')
        self.assertIsNone(amount['currency'])
        self.assertEqual(amount['currency_status'],'not_recorded')

    def test_missing_financial_evidence_does_not_become_an_authoritative_zero(self):
        self.local.reason.return_value='You earn INR 900000 every month.'
        result=self.answer('finance')
        self.assertNotIn('900000',result['answer']); self.assertEqual(result['provider'],'local_evidence')
        self.local.reason.assert_not_called()
        amount=result['sources'][0]['data']['amounts']['monthly_income']
        self.assertIsNone(amount['amount'])
        self.assertEqual(amount['evidence_status'],'unavailable')

    def test_checked_source_references_do_not_suppress_non_numeric_interpretation(self):
        self.local.reason.return_value=f'Review your verified closure evidence loan-closure-{self.document.pk}.'
        result=self.answer()
        self.assertFalse(result['narrative_withheld'])
        self.assertIn('Review your verified',result['answer'])

    def test_general_money_claim_without_canonical_evidence_is_not_displayed_as_fact(self):
        self.local.reason.return_value='Your personal balance is 500 euros.'
        result=self.answer('general')
        self.assertTrue(result['narrative_withheld'])
        self.assertNotIn('500',result['answer'])

    def test_financial_question_cannot_get_an_unlabelled_numeric_general_answer(self):
        self.local.reason.return_value='500.00'
        result=hybrid_answer(self.store,self.user,'What is my bank balance?',local=self.local)
        self.assertTrue(result['narrative_withheld'])
        self.assertNotIn('500.00',result['answer'])

    def test_travel_numbers_are_not_formatted_or_suppressed_as_money(self):
        self.local.reason.return_value='Consider 3 quiet walks as a hypothesis.'
        result=self.answer('travel')
        self.assertFalse(result['narrative_withheld'])
        self.assertIn('3 quiet walks',result['answer'])

    def test_currency_explanation_without_personal_financial_figures_is_allowed(self):
        self.local.reason.return_value='USD and EUR are different currency codes.'
        self.assertFalse(self.answer('general')['narrative_withheld'])

    def test_unicode_currency_and_financial_numbers_are_also_withheld(self):
        for text in ('Your budget is ¥500.','Your loan balance is ١٢٣.','The closure cost 100.00.'):
            self.local.reason.return_value=text
            self.assertTrue(self.answer()['narrative_withheld'])
