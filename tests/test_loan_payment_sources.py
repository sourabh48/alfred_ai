"""Read-only payment associations reuse transaction evidence, never settlement calculations."""
from datetime import date
import json
from pathlib import Path
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import Http404
from django.test import TestCase, Client

from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.expenses.services.statement_evidence import evidence, review
from apps.expenses.services.statement_lifecycle import _import_statement_transactions
from apps.loans.models import Loan, LoanPaymentHistory
from apps.ml_engine.services.canonical_evidence import record_source
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
from apps.ml_engine.services.persistent_memory import MemoryConflict
from tests import test_canonical_grounding as fixtures
from tests.test_expense_money_identity import parsed_fixture


class LoanPaymentSourceTests(TestCase):
    def setUp(self):
        fixtures.CanonicalGroundingTests.setUp(self)
        self.payment=LoanPaymentHistory.objects.create(loan=self.loan,payment_date=date(2026,9,1),amount='100.01',
            match_status='matched',loan_effect_applied=True,expense_reference=self.expense)

    def source(self): return record_source(self.owner,'loan',self.loan.pk)

    def answer(self):
        return hybrid_answer(self.store,self.owner,'Show my repayment status',scope='financial_records',
            record_type='loan',record_id=self.loan.pk,local=self.local)

    def bank_source(self):
        self.upload=StatementUpload.objects.create(user=self.owner,bank_account=self.account,account_number=self.account.account_number,
            original_file=SimpleUploadedFile('synthetic-private-statement.pdf',b'%PDF-SYNTHETIC-PAYMENT'),
            file_name='SYNTHETIC-PRIVATE-STATEMENT.pdf',parser_status='parsed',extracted_payload={'raw':'SYNTHETIC-NEVER-MODEL'})
        _import_statement_transactions(user=self.owner,upload=self.upload,bank_account=self.account,parsed=parsed_fixture())
        self.bank_row=Expense.objects.get(statement_upload=self.upload)
        self.payment.expense_reference=self.bank_row; self.payment.save(update_fields=['expense_reference'])

    def confirm(self, *, revoke=False):
        return review(self.owner,self.bank_row.pk,revision=evidence(self.owner,self.bank_row.pk)['revision'],confirm=True,revoke=revoke)

    def test_manual_reference_is_owner_recorded_without_amount_matching_or_financial_writes(self):
        models=(Loan,LoanPaymentHistory,Expense,BankAccount,type(self.owner))
        before=[list(model.objects.order_by('pk').values()) for model in models]
        baseline=resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts']
        source=self.source(); reference=source['data']['applied_payment_source']
        self.assertEqual(reference['url'],record_source(self.owner,'expense',self.expense.pk)['url'])
        self.assertEqual(reference['evidence_status'],'owner_recorded_transaction_reference')
        self.assertIn('recorded association only',' '.join(source['data']['limitations']))
        self.assertNotIn('amount',reference)
        self.assertEqual(source['data']['amounts']['emi']['amount'],'100.01')
        self.assertEqual(resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts'],baseline)
        self.assertEqual([list(model.objects.order_by('pk').values()) for model in models],before)

    def test_bank_confirmation_correction_and_revocation_revalidate_reference_not_loan_amounts(self):
        self.bank_source(); original_fingerprint=self.bank_row.transaction_fingerprint
        self.assertEqual(self.source()['data']['applied_payment_source']['evidence_status'],'unverified_transaction_reference')
        self.confirm(); source=self.source(); reference=source['data']['applied_payment_source']
        self.assertEqual(reference['evidence_status'],'owner_confirmed_statement_reference')
        self.assertEqual(reference['url'],evidence(self.owner,self.bank_row.pk)['citation_url'])
        self.assertIn(reference['url'],self.client.get(source['url']).content.decode())
        self.confirm(revoke=True)
        self.assertNotEqual(self.source()['revision'],source['revision'])
        self.assertEqual(self.source()['data']['applied_payment_source']['evidence_status'],'unverified_transaction_reference')
        self.confirm(); before=self.source()
        Expense.objects.filter(pk=self.bank_row.pk).update(amount='3.45')
        after=self.source(); self.assertNotEqual(after['revision'],before['revision'])
        self.assertEqual({name:value['amount'] for name,value in after['data']['amounts'].items()},
            {name:value['amount'] for name,value in before['data']['amounts'].items()})
        self.assertEqual(after['data']['applied_payment_source']['evidence_status'],'unverified_transaction_reference')
        self.bank_row.refresh_from_db(); self.assertEqual(self.bank_row.transaction_fingerprint,original_fingerprint)

    def test_bank_source_changes_during_inference_reject_stale_association(self):
        self.bank_source(); contents=Path(self.upload.original_file.path).read_bytes()
        changes=[lambda:self.confirm(revoke=True),lambda:Path(self.upload.original_file.path).unlink(),
            lambda:Path(self.upload.original_file.path).write_bytes(b'%PDF-SYNTHETIC-CHANGED'),
            lambda:StatementUpload.objects.filter(pk=self.upload.pk).update(user=self.other),
            lambda:Expense.objects.filter(pk=self.bank_row.pk).update(user=self.other),
            lambda:Expense.objects.filter(pk=self.bank_row.pk).delete()]
        for index,change in enumerate(changes):
            with self.subTest(change=index),transaction.atomic():
                self.confirm()
                def changed(*args,**kwargs): change(); return 'Synthetic association context.'
                self.local.reason.side_effect=changed
                with self.assertRaises(MemoryConflict): self.answer()
                transaction.set_rollback(True)
            Path(self.upload.original_file.path).write_bytes(contents)

    def test_missing_file_deleted_statement_and_deleted_transaction_never_keep_verified_reference(self):
        self.bank_source(); self.confirm(); Path(self.upload.original_file.path).unlink()
        reference=self.source()['data']['applied_payment_source']
        self.assertEqual(reference['evidence_status'],'unverified_transaction_reference')
        self.upload.delete(); reference=self.source()['data']['applied_payment_source']
        self.assertEqual(reference['verification'],'source_not_retained'); self.assertIsNone(reference['url'])
        self.bank_row.delete(); reference=self.source()['data']['applied_payment_source']
        self.assertEqual(reference['verification'],'source_not_retained'); self.assertIsNone(reference['transaction_id'])
        self.assertTrue(self.source()['available'])

    def test_cross_account_and_parent_account_ownership_are_enforced(self):
        self.bank_source(); self.confirm()
        source=self.source(); urls=(source['url'],source['data']['applied_payment_source']['url'])
        for actor in (None,self.other):
            client=Client()
            if actor: client.force_login(actor)
            for url in urls: self.assertIn(client.get(url).status_code,(302,403,404))
        BankAccount.objects.filter(pk=self.account.pk).update(user=self.other)
        with self.assertRaises(Http404): self.source()

    def test_private_bank_data_and_nested_citations_never_enter_local_prompt_or_cloud(self):
        self.bank_source(); self.confirm(); result=self.answer()
        self.assertEqual(result['provider'],'ollama'); payload=json.dumps(self.local.reason.call_args.args[0])
        for secret in ('SYNTHETIC-PRIVATE-STATEMENT','SYNTHETIC-NEVER-MODEL','/documents/statements/',self.account.account_number,'applied_payment_source'):
            self.assertNotIn(secret,payload)
        self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_expense_reparented_between_loan_guard_and_owner_lookup_is_denied(self):
        original=Expense.objects.filter
        def changed(*args,**kwargs):
            if kwargs.get('pk')==self.expense.pk and kwargs.get('user')==self.owner:
                original(pk=self.expense.pk).update(user=self.other)
            return original(*args,**kwargs)
        with patch.object(Expense.objects,'filter',side_effect=changed),self.assertRaises(Http404): self.source()

    def test_unapplied_or_rejected_matches_do_not_generate_payment_source(self):
        for status in ('review','rejected'):
            LoanPaymentHistory.objects.filter(pk=self.payment.pk).update(match_status=status,loan_effect_applied=False)
            self.assertNotIn('applied_payment_source',self.source()['data'])
        LoanPaymentHistory.objects.filter(pk=self.payment.pk).update(match_status='review',loan_effect_applied=True)
        self.assertFalse(self.source()['available'])
