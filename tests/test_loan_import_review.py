"""Synthetic loan review acceptance through real Decimal posting and source storage."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings

from alfred_ai.services.document_review import _retry_loan_document, apply_correction, delete_document
from apps.loans.models import Loan, LoanImportDocument, LoanPaymentHistory
from apps.loans.services.import_review import stage_loan_document, loan_preview, confirm_loan_review, LoanReviewConflict
from apps.loans.services.loan_pdf_parser import loan_pdf_parser
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_statement_metadata_security import statement_pdf


def extraction(**changes):
    row = dict(lender='Synthetic Finance', loan_type='personal', loan_account_number='SYNTHETIC-LN-01',
        principal='10000.015', remaining_balance='8000.005', interest_rate=10.5, emi='500.005',
        tenure_months=24, start_date='2025-01-01', currency='INR')
    row.update(changes)
    return dict(document_type='sanction_letter', confidence=.9, extracted_text='Synthetic owner-approved fixture', loans=[row])


class LoanImportReviewTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-loan-review-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media', ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='synthetic-loan-review-owner')
        self.other = get_user_model().objects.create_user(username='synthetic-loan-review-other')
        self.client.force_login(self.owner)

    def stage(self, parsed=None, owner=None):
        return stage_loan_document(user=owner or self.owner, parsed=parsed or extraction(),
            upload_file=SimpleUploadedFile('synthetic-loan.pdf', b'%PDF-1.4 synthetic retained source', content_type='application/pdf'))

    def confirm(self, document, token=None):
        return self.client.post(f'/api/loans/import-uploads/{document.pk}/confirm/',
            {'confirm': True, 'token': token or loan_preview(document)['token']}, content_type='application/json')

    def test_stage_before_write_then_decimal_confirmation_is_single_use_and_retains_source(self):
        doc = self.stage()
        self.assertFalse(Loan.objects.exists()); self.assertFalse(LoanPaymentHistory.objects.exists())
        preview = loan_preview(doc)
        self.assertTrue(preview['can_confirm'])
        first = self.confirm(doc, preview['token'])
        self.assertEqual(first.status_code, 200, first.content)
        loan = Loan.objects.get()
        self.assertEqual((loan.principal, loan.emi, loan.remaining_balance), (Decimal('10000.02'), Decimal('500.01'), Decimal('8000.01')))
        before = list(Loan.objects.values())
        replay = self.confirm(doc, preview['token'])
        self.assertTrue(replay.json()['replayed'])
        self.assertEqual(list(Loan.objects.values()), before)
        self.assertTrue(Path(doc.uploaded_file.path).exists())

    def test_existing_matching_loan_is_linked_without_changing_any_register_field(self):
        existing = Loan.objects.create(user=self.owner, lender='Synthetic Finance', loan_account_number='SYNTHETIC-LN-01',
            principal='20000', remaining_balance='17000', emi='900', interest_rate=11, tenure_months=48,
            start_date=date(2024, 1, 1), currency='INR')
        before = list(Loan.objects.values())
        doc = self.stage()
        preview = loan_preview(doc)
        self.assertEqual(preview['rows'][0]['action'], 'link')
        self.assertIn('remaining_balance', preview['rows'][0]['conflicts'])
        self.assertEqual(self.confirm(doc).status_code, 200)
        self.assertEqual(list(Loan.objects.values()), before)
        self.assertEqual(list(doc.linked_loans.values_list('pk', flat=True)), [existing.pk])

    def test_missing_invalid_currency_and_zero_balance_stay_unresolved(self):
        for changes in ({'currency': None}, {'currency': 'ZZZ'}, {'remaining_balance': None},
                        {'remaining_balance': 0}, {'principal': None}, {'emi': None}, {'start_date': None}):
            with self.subTest(changes=changes):
                doc = self.stage(extraction(**changes))
                self.assertFalse(loan_preview(doc)['can_confirm'])
                self.assertEqual(self.confirm(doc).status_code, 409)
        self.assertFalse(Loan.objects.exists())

    def test_corrections_preserve_original_and_stale_confirmation_is_rejected(self):
        doc = self.stage(extraction(currency=None))
        old = loan_preview(doc)['token']
        response = self.client.patch(f'/api/loans/import-uploads/{doc.pk}/preview/',
            {'revision': 0, 'edits': [{'index': 0, 'currency': 'USD', 'principal': '12345.67'}]}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.confirm(doc, old).status_code, 409)
        doc.refresh_from_db()
        self.assertIsNone(doc.extracted_payload['import_review']['original'][0]['currency'])
        self.assertEqual(self.confirm(doc).status_code, 200)
        loan = Loan.objects.get()
        self.assertEqual((loan.currency, loan.principal), ('USD', Decimal('12345.67')))
        self.assertFalse(Loan.objects.in_rupee_totals().exists())

    def test_owner_csrf_expiry_and_stale_loan_revision(self):
        doc = self.stage()
        token = loan_preview(doc)['token']
        outsider = Client(); outsider.force_login(self.other)
        path = f'/api/loans/import-uploads/{doc.pk}'
        self.assertEqual(outsider.get(path+'/preview/').status_code, 404)
        self.assertEqual(outsider.post(path+'/confirm/', {'confirm': True, 'token': token}, content_type='application/json').status_code, 404)
        guarded = Client(enforce_csrf_checks=True); guarded.force_login(self.owner)
        self.assertEqual(guarded.post(path+'/confirm/', {'confirm': True, 'token': token}, content_type='application/json').status_code, 403)
        with patch('django.core.signing.time.time', return_value=0): expired = loan_preview(doc)['token']
        self.assertEqual(self.confirm(doc, expired).status_code, 409)
        other_doc = self.stage(); self.assertEqual(self.confirm(other_doc).status_code, 200)
        self.assertEqual(self.confirm(doc, token).status_code, 409)
        doc.refresh_from_db()
        self.client.patch(path+'/preview/', {'revision': 0, 'edits': [{'index': 0, 'action': 'link', 'target_id': Loan.objects.get().pk}]}, content_type='application/json')
        doc.refresh_from_db(); token = loan_preview(doc)['token']
        Loan.objects.update(remaining_balance=Decimal('7000'))
        self.assertEqual(self.confirm(doc, token).status_code, 409)

    def test_duplicate_bytes_and_repeated_rows_do_not_create_duplicate_loans(self):
        first = self.stage(); self.assertEqual(self.confirm(first).status_code, 200)
        second = self.stage()
        self.assertIn(first.pk, loan_preview(second)['duplicate_documents'])
        self.assertEqual(self.confirm(second).status_code, 200)
        self.assertEqual(Loan.objects.count(), 1)
        self.assertEqual(LoanImportDocument.objects.count(), 2)
        for doc in (first, second): self.assertTrue(Path(doc.uploaded_file.path).exists())
        parsed = extraction(loan_account_number='SECOND-SYNTHETIC-ACCOUNT')
        parsed['loans'].append(deepcopy(parsed['loans'][0]))
        third = self.stage(parsed)
        self.assertEqual(loan_preview(third)['rows'][1]['action'], 'skip')
        self.assertEqual(self.confirm(third).status_code, 200)
        self.assertEqual(Loan.objects.count(), 2)

    def test_failed_posting_rolls_back_and_can_be_retried(self):
        doc = self.stage(); token = loan_preview(doc)['token']
        with patch('apps.loans.services.import_review.capture_import', side_effect=OperationalError('Synthetic receipt failure')):
            self.assertEqual(self.confirm(doc, token).status_code, 409)
        self.assertFalse(Loan.objects.exists())
        doc.refresh_from_db(); self.assertEqual(doc.extracted_payload['import_review']['state'], 'pending')
        self.assertEqual(self.confirm(doc, token).status_code, 200)

    def test_retry_race_and_edited_draft_are_preserved_without_posting(self):
        doc = self.stage()
        def parse(*args, **kwargs):
            self.assertEqual(self.confirm(doc).status_code, 200)
            return extraction()
        with patch('alfred_ai.services.document_review.loan_pdf_parser.parse_document', side_effect=parse):
            with self.assertRaises(LoanReviewConflict): _retry_loan_document(self.owner, doc.pk)
        doc.refresh_from_db(); self.assertEqual(doc.extracted_payload['import_review']['state'], 'confirmed')
        draft = self.stage(extraction(loan_account_number='EDITED-DRAFT'))
        self.client.patch(f'/api/loans/import-uploads/{draft.pk}/preview/',
            {'revision': 0, 'edits': [{'index': 0, 'emi': '123.45'}]}, content_type='application/json')
        with self.assertRaises(LoanReviewConflict): _retry_loan_document(self.owner, draft.pk)
        draft.refresh_from_db(); self.assertEqual(draft.extracted_payload['import_review']['candidate'][0]['emi'], '123.45')

    def test_source_change_invalidates_confirmation_and_source_delete_preserves_loan(self):
        doc = self.stage(); token = loan_preview(doc)['token']
        Path(doc.uploaded_file.path).write_bytes(b'%PDF-1.4 synthetic changed source')
        self.assertEqual(self.confirm(doc, token).status_code, 409)
        confirmed = self.stage(); self.assertEqual(self.confirm(confirmed).status_code, 200)
        before = list(Loan.objects.values())
        delete_document(self.owner, scope='loan_document', document_id=confirmed.pk)
        self.assertEqual(list(Loan.objects.values()), before)

    def test_legacy_correction_edits_draft_without_updating_existing_loan(self):
        doc = self.stage(); self.assertEqual(self.confirm(doc).status_code, 200)
        before = list(Loan.objects.values())
        apply_correction(self.owner, scope='loan_document', document_id=doc.pk, corrections={'lender': 'Owner-corrected source name'})
        self.assertEqual(list(Loan.objects.values()), before)
        doc.refresh_from_db(); self.assertEqual(doc.extracted_payload['import_review']['state'], 'pending')

    def test_real_pdf_extraction_is_decimal_and_missing_terms_are_not_invented(self):
        source = statement_pdf('HDFC PERSONAL LOAN', 'Loan Account Number: SYNTHETIC-01',
            'Principal Amount: 10000.015', 'Outstanding Amount: 8000.005', 'EMI Amount: 500.005',
            'ROI: 10.5%', 'Tenure: 24 Months', 'Start Date: 01/01/2025', 'Currency: INR')
        with patch('apps.loans.services.loan_pdf_parser.apply_parser_learning', side_effect=lambda **kwargs: (kwargs['confidence'], [])):
            parsed = loan_pdf_parser.parse_document(SimpleUploadedFile('synthetic-real.pdf', source))
        self.assertEqual(parsed['loans'][0]['principal'], Decimal('10000.02'))
        self.assertEqual(parsed['loans'][0]['remaining_balance'], Decimal('8000.01'))
        response = self.client.post('/api/loans/import-pdf/',
            {'file': SimpleUploadedFile('synthetic-real.pdf', source, content_type='application/pdf')})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(Loan.objects.exists())
        document = LoanImportDocument.objects.get(pk=response.json()['upload']['id'])
        self.assertTrue(loan_preview(document)['can_confirm'])
        self.assertEqual(self.confirm(document).status_code, 200)
        self.assertEqual(Loan.objects.get().principal, Decimal('10000.02'))
        missing = loan_pdf_parser._extract_loan_details('HDFC PERSONAL LOAN Principal Amount: 10000')
        for field in ('remaining_balance', 'emi', 'interest_rate', 'tenure_months', 'start_date', 'currency'):
            self.assertIsNone(missing[field], field)

    def test_invalid_file_formats_and_malformed_financial_corrections_do_not_post(self):
        bad = self.client.post('/api/loans/import-pdf/', {'file': SimpleUploadedFile('wrong.txt', b'not a PDF')})
        self.assertEqual(bad.status_code, 400)
        doc = self.stage()
        for field, value in (('principal', 'NaN'), ('emi', 'Infinity'), ('emi', '-1'), ('tenure_months', '1.5'), ('interest_rate', True)):
            response = self.client.patch(f'/api/loans/import-uploads/{doc.pk}/preview/',
                {'revision': 0, 'edits': [{'index': 0, field: value}]}, content_type='application/json')
            self.assertEqual(response.status_code, 400, (field, value, response.content))
        self.assertFalse(Loan.objects.exists())


class LoanConcurrentConfirmationTests(TransactionTestCase):
    def test_simultaneous_confirmations_never_post_twice_and_retry_is_safe(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-loan-race-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media', ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(_offline_fixture_patches())
        owner = get_user_model().objects.create_user(username='synthetic-concurrent-loan-owner')
        document = stage_loan_document(user=owner, parsed=extraction(),
            upload_file=SimpleUploadedFile('synthetic-race.pdf', b'%PDF-1.4 synthetic retained source'))
        token = loan_preview(document)['token']
        barrier = Barrier(2, timeout=10)

        def synchronized_preview(*args, **kwargs):
            preview = loan_preview(*args, **kwargs)
            barrier.wait()
            return preview

        def confirm():
            try:
                return confirm_loan_review(document, token=token)
            except (OperationalError, LoanReviewConflict):
                return 'retry'
            finally:
                connections.close_all()

        with patch('apps.loans.services.import_review.loan_preview', side_effect=synchronized_preview):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: confirm(), range(2)))
        self.assertTrue(all(isinstance(result, dict) or result == 'retry' for result in results))
        self.assertLessEqual(Loan.objects.count(), 1)
        confirm_loan_review(document, token=token)
        before = list(Loan.objects.values())
        self.assertTrue(confirm_loan_review(document, token=token)['replayed'])
        self.assertEqual(Loan.objects.count(), 1)
        self.assertEqual(list(Loan.objects.values()), before)
        self.assertFalse(LoanPaymentHistory.objects.exists())

