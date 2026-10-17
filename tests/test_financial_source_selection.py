"""Bounded explicit source selection; all records/files/providers are synthetic."""
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import Http404
from django.test import Client, TestCase, override_settings

from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.investments.models import InvestmentImportDocument
from apps.investments.services import document_evidence as investment_evidence
from apps.loans.models import LoanImportDocument
from apps.loans.services import document_evidence as loan_evidence
from apps.ml_engine.services import canonical_evidence as sources
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
from apps.ml_engine.services.persistent_memory import MemoryConflict
from tests import test_canonical_grounding as fixtures


class FinancialSourceSelectionTests(TestCase):
    def setUp(self):
        fixtures.CanonicalGroundingTests.setUp(self)

    def documents(self, kind='investment', count=7):
        model=InvestmentImportDocument if kind=='investment' else LoanImportDocument
        service=investment_evidence if kind=='investment' else loan_evidence
        row=self.rows[kind]; result=[]
        for index in range(count):
            document=model.objects.create(user=self.owner,file_name=f'SYNTHETIC-PRIVATE-{kind}-{index}.pdf',
                uploaded_file=SimpleUploadedFile('synthetic.pdf',f'%PDF-SYNTHETIC-{kind}-{index}'.encode()),
                parser_status='parsed',extracted_text='SYNTHETIC-NOT-MODEL-OR-CLOUD')
            getattr(document,f'linked_{kind}s').add(row)
            service.capture_import(document,[row])
            detail=service.evidence(self.owner,document.pk,row.pk)
            service.review(self.owner,document.pk,row.pk,revision=detail['revision'],fields=list(service.FIELDS),confirm=True)
            result.append(document)
        return result

    def pages(self, kind='investment'):
        page=sources.document_page(self.owner,kind,self.rows[kind].pk); first=page; items=list(page['items'])
        while page['next_cursor']:
            page=sources.document_page(self.owner,kind,self.rows[kind].pk,cursor=page['next_cursor'])
            items+=page['items']
            self.assertEqual(page['catalog_token'],first['catalog_token'])
        return first,items

    def selection(self, items):
        return [dict(id=item['document_id'],revision=item['revision']) for item in items]

    def answer(self, page, items, kind='investment', **changes):
        return hybrid_answer(self.store,self.owner,'Explain this record',**(dict(scope='financial_records',
            record_type=kind,record_id=self.rows[kind].pk,local=self.local,
            selected_documents=self.selection(items),source_catalog=page['catalog_token'])|changes))

    def post(self, page, items, kind='investment', **changes):
        return self.client.post('/api/ai/personal-insights/',dict(query='Explain this record',scope='financial_records',
            record_type=kind,record_id=self.rows[kind].pk,selected_documents=self.selection(items),
            source_catalog=page['catalog_token'])|changes,content_type='application/json')

    def test_all_pages_are_complete_deterministic_owner_scoped_and_hash_at_most_five_files(self):
        for kind in ('loan','investment'):
            with self.subTest(kind=kind):
                documents=self.documents(kind)
                with patch.object(sources,'_document_evidence',wraps=sources._document_evidence) as read:
                    first=sources.document_page(self.owner,kind,self.rows[kind].pk)
                    self.assertEqual(read.call_count,5)
                page,items=self.pages(kind)
                self.assertEqual([item['document_id'] for item in items],[d.pk for d in documents])
                self.assertEqual(page['count'],7); self.assertEqual(page['limit'],5)
                self.assertEqual(first['items'],items[:5])
                for item in items:
                    self.assertTrue(item['selectable']); self.assertEqual(item['verification'],'owner_confirmed')
                    self.assertEqual(item['freshness'],'current_review'); self.assertTrue(item['uploaded_at'])
                    self.assertEqual(self.client.get(item['url']).status_code,200)
                url=f'/api/ai/financial-evidence/{kind}/{self.rows[kind].pk}/documents/'
                response=self.client.get(url); self.assertEqual(response.status_code,200)
                self.assertIn('no-store',response['Cache-Control'])
                self.client.force_login(self.other); self.assertEqual(self.client.get(url).status_code,404)
                self.assertEqual(self.client.get(items[-1]['url']).status_code,404)
                self.client.logout(); self.assertIn(self.client.get(url).status_code,(401,403))
                self.client.force_login(self.owner)

    def test_explicit_older_and_multiple_sources_preserve_values_references_and_prompt_budget(self):
        for kind in ('loan','investment'):
            self.documents(kind); page,items=self.pages(kind)
            self.assertFalse(sources.record_source(self.owner,kind,self.rows[kind].pk)['available'])
            result=self.answer(page,[items[-1],items[0]],kind)
            self.assertEqual(result['provider'],'ollama')
            source=result['sources'][0]; data=source['data']
            self.assertEqual([s['document_id'] for s in data['document_sources']],[items[0]['document_id'],items[-1]['document_id']])
            self.assertEqual(data['document_selection'],dict(mode='explicit',selected_count=2,linked_count=7,unselected_count=5,limit=5))
            service=loan_evidence if kind=='loan' else investment_evidence
            for field in service.FIELDS:
                value=data['amounts'][field]
                self.assertEqual(value['amount'],format(Decimal(str(getattr(self.rows[kind],field))),'.2f'))
                self.assertIsNone(value['currency']); self.assertEqual(value['currency_status'],'not_recorded')
            prompt=json.dumps(self.local.reason.call_args.args[0])
            self.assertLessEqual(len(prompt.encode()),4096)
            for private in ('SYNTHETIC-PRIVATE','SYNTHETIC-NOT-MODEL-OR-CLOUD','catalog_token','/documents/',page['catalog_token']):
                self.assertNotIn(private,prompt)
            single=self.answer(page,[items[-1]],kind)['sources'][0]
            self.assertEqual(single['url'],items[-1]['url'])
        self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_bad_over_budget_duplicate_or_unsupported_selections_are_never_silently_truncated(self):
        self.documents(); page,items=self.pages()
        for selection in ([],self.selection(items[:6]),self.selection([items[0],items[0]]),
                [dict(id=True,revision=items[0]['revision'])],[dict(id=items[0]['document_id'],revision='invalid')],
                [dict(id=items[0]['document_id'],revision=items[0]['revision'],owner=self.owner.pk)]):
            with self.subTest(selection=selection):
                self.assertEqual(self.post(page,[],selected_documents=selection).status_code,400)
        self.assertEqual(self.post(page,items[:1],source_catalog='tampered').status_code,400)
        self.assertEqual(self.post(page,items[:1],source_catalog=None).status_code,400)
        self.assertEqual(self.post(page,items[:1],record_type='baseline',record_id=self.owner.pk).status_code,400)
        self.assertEqual(self.post(page,items[:1],record_type='budget',record_id=self.budget.pk).status_code,400)
        self.assertEqual(self.post(page,items[:1],scope='general',record_type=None,record_id=None).status_code,400)
        self.assertEqual(self.post(page,items[:1],cloud_consent=True).status_code,403)
        csrf=Client(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post('/api/ai/personal-insights/',{}).status_code,403)
        self.local.reason.assert_not_called()

    def test_cursor_tampering_owner_replay_expiry_and_catalog_membership_changes_fail_closed(self):
        documents=self.documents(); page,items=self.pages()
        with self.assertRaises(ValueError): sources.document_page(self.owner,'investment',self.investment.pk,cursor='tampered')
        with patch('django.core.signing.time.time',return_value=9999999999):
            self.assertEqual(self.post(page,items[:1]).status_code,409)
        other=type(self.investment).objects.create(user=self.other,asset_type='equity',invested_amount='1.00')
        self.client.force_login(self.other)
        self.assertEqual(self.post(page,items[:1],record_id=other.pk).status_code,404)
        self.client.force_login(self.owner)
        for change in (lambda:documents[-1].linked_investments.clear(),
                lambda:(documents[0].linked_investments.clear(),documents[0].linked_investments.add(self.investment)),
                lambda:type(self.investment).objects.filter(pk=self.investment.pk).update(current_value='4567.89')):
            with transaction.atomic():
                change()
                with self.assertRaises(sources.SourceSelectionConflict):
                    sources.document_page(self.owner,'investment',self.investment.pk,cursor=page['next_cursor'])
                self.assertEqual(self.post(page,items[:1]).status_code,409)
                transaction.set_rollback(True)
        self.local.reason.assert_not_called()

    def test_unreviewed_revoked_missing_changed_and_foreign_sources_never_reach_inference(self):
        documents=self.documents(); page,items=self.pages()
        document=documents[-1]; contents=Path(document.uploaded_file.path).read_bytes()
        changes=[lambda:investment_evidence.review(self.owner,document.pk,self.investment.pk,
            revision=investment_evidence.evidence(self.owner,document.pk,self.investment.pk)['revision'],
            fields=['current_value'],confirm=True,revoke=True),
            lambda:Path(document.uploaded_file.path).unlink(),
            lambda:Path(document.uploaded_file.path).write_bytes(b'%PDF-SYNTHETIC-CHANGED'),
            lambda:InvestmentImportDocument.objects.filter(pk=document.pk).update(parser_status='failed'),
            lambda:InvestmentImportDocument.objects.filter(pk=document.pk).update(user=self.other)]
        for index,change in enumerate(changes):
            with self.subTest(index=index),transaction.atomic():
                change(); response=self.post(page,[items[-1]])
                self.assertIn(response.status_code,(404,409))
                self.assertNotIn('SYNTHETIC-PRIVATE',response.content.decode())
                transaction.set_rollback(True)
            Path(document.uploaded_file.path).write_bytes(contents)
        self.local.reason.assert_not_called()

    def test_distinct_records_of_identical_file_are_conflict_not_silently_deduplicated(self):
        documents=self.documents(count=2)
        Path(documents[-1].uploaded_file.path).write_bytes(Path(documents[0].uploaded_file.path).read_bytes())
        detail=investment_evidence.evidence(self.owner,documents[-1].pk,self.investment.pk)
        investment_evidence.review(self.owner,documents[-1].pk,self.investment.pk,
            revision=detail['revision'],fields=list(investment_evidence.FIELDS),confirm=True)
        page,items=self.pages(); response=self.post(page,items)
        self.assertEqual(response.status_code,409); self.assertEqual(response.json()['code'],'financial_sources_changed')
        self.local.reason.assert_not_called()

    def test_post_inference_source_change_rejects_answer_without_financial_mutation(self):
        documents=self.documents(); page,items=self.pages()
        def revoke(*args,**kwargs):
            detail=investment_evidence.evidence(self.owner,documents[-1].pk,self.investment.pk)
            investment_evidence.review(self.owner,documents[-1].pk,self.investment.pk,
                revision=detail['revision'],fields=['current_value'],confirm=True,revoke=True)
            return 'SYNTHETIC-DO-NOT-RETURN'
        self.local.reason.side_effect=revoke
        response=self.post(page,[items[-1]])
        self.assertEqual(response.status_code,409)
        self.assertNotIn('SYNTHETIC-DO-NOT-RETURN',response.content.decode())
        self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_paging_and_answers_are_financially_read_only_with_no_memory_promotion(self):
        self.documents(); models=tuple(type(row) for row in self.rows.values())+(type(self.account),)
        before=[list(model.objects.order_by('pk').values()) for model in models]
        baseline=resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts']
        page,items=self.pages(); self.answer(page,items[-2:])
        self.assertEqual([list(model.objects.order_by('pk').values()) for model in models],before)
        self.assertEqual(resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts'],baseline)
        self.assertEqual(self.store.list_memories(self.owner),[])

    def test_page_change_during_retrieval_is_rejected(self):
        documents=self.documents()
        original=sources._document_evidence
        def changing(*args):
            detail=original(*args); documents[-1].linked_investments.clear(); return detail
        with patch.object(sources,'_document_evidence',side_effect=changing):
            with self.assertRaises(sources.SourceSelectionConflict):
                sources.document_page(self.owner,'investment',self.investment.pk)

    def test_single_banked_transaction_uses_same_review_and_citation_boundary(self):
        from apps.expenses.models import Expense, StatementUpload
        from apps.expenses.services import statement_evidence as bank
        from apps.expenses.services.statement_lifecycle import _import_statement_transactions
        from tests.test_expense_money_identity import parsed_fixture
        upload=StatementUpload.objects.create(user=self.owner,bank_account=self.account,account_number=self.account.account_number,
            original_file=SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC-BANK-ONLY'),file_name='synthetic-bank.pdf',parser_status='parsed')
        _import_statement_transactions(user=self.owner,upload=upload,bank_account=self.account,parsed=parsed_fixture())
        row=Expense.objects.get(statement_upload=upload); self.rows['expense']=row
        page,items=self.pages('expense'); self.assertFalse(items[0]['selectable'])
        self.assertEqual(self.post(page,items,'expense').status_code,409)
        detail=bank.evidence(self.owner,row.pk); bank.review(self.owner,row.pk,revision=detail['revision'],confirm=True)
        page,items=self.pages('expense'); result=self.answer(page,items,'expense')
        source=result['sources'][0]; self.assertEqual(source['url'],items[0]['url'])
        self.assertEqual(source['data']['amounts']['amount']['amount'],'2.68')
        detail=bank.evidence(self.owner,row.pk); bank.review(self.owner,row.pk,revision=detail['revision'],confirm=True,revoke=True)
        self.assertEqual(self.post(page,items,'expense').status_code,409)

    def test_history_retains_only_exact_selected_references_and_replay_binds_selection(self):
        from apps.ml_engine.services.conversation_history import ConversationHistory
        self.documents(); page,items=self.pages()
        with override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True):
            history=ConversationHistory(self.store)
            history.configure(self.owner,enabled=True,consent=True,days=7)
            conversation=history.create(self.owner,'Synthetic references')
            parameters=dict(conversation_id=conversation['id'],conversation_revision=0,request_id='a'*32)
            response=self.post(page,[items[0],items[-1]],**parameters)
            self.assertEqual(response.status_code,200)
            saved=history.get(self.owner,conversation['id'])['turns'][0]
            self.assertEqual([ref['url'] for ref in saved['sources'][1:]],[items[0]['url'],items[-1]['url']])
            for ref in saved['sources']:
                self.assertTrue(set(ref)<= {'ref','classification','url','verified_at'})
            self.assertNotIn('2345.67',json.dumps(saved)); self.assertNotIn('SYNTHETIC-PRIVATE',json.dumps(saved))
            self.assertEqual(self.post(page,[items[0]],**parameters).status_code,409)
            self.assertEqual(self.post(page,[items[0],items[-1]],**parameters).json()['historical'],True)
