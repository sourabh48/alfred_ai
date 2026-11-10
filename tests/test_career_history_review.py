"""Synthetic reviewed recovery: no private runtime or provider calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError, connections
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from apps.career.models import CareerJobAnalysis
from apps.career.services import history_review as review
from apps.reports.models import OperationalLog


class CareerHistoryReviewTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='synthetic-history-review')
        self.other = get_user_model().objects.create_user(username='synthetic-history-review-other')
        self.source = {'stage':'applied','history':'PRIVATE-MALFORMED-SOURCE','note':'<img src=x onerror=alert(1)>'}
        self.row = CareerJobAnalysis.objects.create(user=self.owner,
            extracted_payload={'application':deepcopy(self.source), 'resume':'PRIVATE-DO-NOT-DISCLOSE'})
        self.fields = {'stage':'applied', 'on':(timezone.localdate()-timedelta(days=2)).isoformat()}
        self.url = f'/api/career/job-analyses/{self.row.pk}/history-review/'
        self.client.force_login(self.owner)

    def prepare(self):
        return review.prepare(self.owner, self.row.pk, review.inspect(self.owner, self.row.pk)['revision'], self.fields)

    def confirm(self, proposal):
        return review.confirm(self.owner, self.row.pk, proposal['proposal_id'], proposal['fields'], True)

    def test_review_does_not_write_canonical_data_and_confirmation_retains_exact_source(self):
        before = deepcopy(self.row.extracted_payload)
        with patch('socket.socket.connect', side_effect=AssertionError('No provider')):
            proposal = self.prepare()
            self.row.refresh_from_db(); self.assertEqual(self.row.extracted_payload, before)
            result = self.confirm(proposal)
        self.assertFalse(result['already_applied'])
        self.row.refresh_from_db()
        payload = self.row.extracted_payload
        self.assertEqual(payload['resume'], before['resume'])
        self.assertEqual(payload['application_history_recoveries'][0]['previous_application'], self.source)
        self.assertEqual(payload['application']['history'], [self.fields])
        self.assertEqual(payload['application']['follow_ups'], [])
        self.assertTrue(self.confirm(proposal)['already_applied'])
        self.assertEqual(len(review.inspect(self.owner, self.row.pk)['recoveries']), 1)
        self.assertNotIn('PRIVATE-', str(OperationalLog.objects.get().payload))
        self.assertFalse(review.inspect(self.owner, self.row.pk)['can_recover'])

    def test_exact_fields_owner_target_and_confirmation_are_bound(self):
        proposal = self.prepare()
        for fields, consent in ((dict(self.fields, stage='interview'), True), (self.fields, False), (self.fields, 'true')):
            with self.subTest(fields=fields, consent=consent), self.assertRaises(review.ActionError):
                review.confirm(self.owner, self.row.pk, proposal['proposal_id'], fields, consent)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        with self.assertRaises(review.ActionError):
            review.confirm(self.other, self.row.pk, proposal['proposal_id'], self.fields, True)
        second = CareerJobAnalysis.objects.create(user=self.owner, extracted_payload={'application':self.source})
        with self.assertRaises(review.ActionError):
            review.cancel(self.owner, second.pk, proposal['proposal_id'])
        self.assertFalse(self.confirm(proposal)['already_applied'])

    def test_expired_cancelled_stale_and_deleted_proposals_cannot_write(self):
        for mode in ('expired','cancelled','stale','deleted'):
            with self.subTest(mode=mode):
                self.row.extracted_payload = {'application':deepcopy(self.source)}; self.row.save()
                proposal = self.prepare()
                if mode=='expired':
                    record=OperationalLog.objects.latest('id')
                    record.payload['expires_at']=(timezone.now()-timedelta(seconds=1)).isoformat()
                    record.save()
                elif mode=='cancelled':
                    review.cancel(self.owner, self.row.pk, proposal['proposal_id'])
                elif mode=='stale':
                    CareerJobAnalysis.objects.filter(pk=self.row.pk).update(extracted_payload={'application':self.source,'changed':True})
                else:
                    OperationalLog.objects.all().delete()
                with self.assertRaises(review.ActionError):
                    self.confirm(proposal)
                self.row.refresh_from_db(); self.assertNotIn('application_history_recoveries', self.row.extracted_payload)

    def test_failure_rolls_back_claim_archive_and_timeline_then_same_review_retries(self):
        proposal=self.prepare()
        with patch.object(OperationalLog, 'save', side_effect=OperationalError('PRIVATE-FAILURE')):
            with self.assertRaises(OperationalError): self.confirm(proposal)
        self.row.refresh_from_db(); self.assertEqual(self.row.extracted_payload['application'], self.source)
        self.assertEqual(OperationalLog.objects.get().event_type, 'career_history_pending')
        self.assertFalse(self.confirm(proposal)['already_applied'])

    def test_invalid_dates_missing_fields_unsupported_bounds_and_fresh_source_are_refused(self):
        revision=review.inspect(self.owner, self.row.pk)['revision']
        for fields in ({}, dict(self.fields, on=''), dict(self.fields, on='bad'),
                dict(self.fields, on=(timezone.localdate()+timedelta(days=1)).isoformat()),
                dict(self.fields, owner_id=self.other.pk), dict(self.fields, stage='guess'), dict(self.fields,on='2026-W44-1')):
            with self.subTest(fields=fields), self.assertRaises(review.ActionError):
                review.prepare(self.owner, self.row.pk, revision, fields)
        with self.assertRaises(review.ActionConflict):
            review.prepare(self.owner, self.row.pk, 'stale', self.fields)
        self.row.extracted_payload={'application':{'stage':'applied','note':'x'*17000}}; self.row.save()
        self.assertFalse(review.inspect(self.owner, self.row.pk)['can_recover'])
        with self.assertRaises(review.ActionError): self.prepare()
        self.assertFalse(OperationalLog.objects.exists())

    def test_replay_after_later_edit_never_overwrites_and_archive_bounds_preserve_sources(self):
        proposal=self.prepare(); self.confirm(proposal)
        payload=CareerJobAnalysis.objects.get(pk=self.row.pk).extracted_payload
        payload['application']['owner_note']='LATER-OWNER-EDIT'
        CareerJobAnalysis.objects.filter(pk=self.row.pk).update(extracted_payload=payload)
        self.assertTrue(self.confirm(proposal)['already_applied'])
        self.assertEqual(CareerJobAnalysis.objects.get(pk=self.row.pk).extracted_payload,payload)
        payload['application']=self.source
        payload['application_history_recoveries']*=5
        CareerJobAnalysis.objects.filter(pk=self.row.pk).update(extracted_payload=payload)
        self.assertFalse(review.inspect(self.owner,self.row.pk)['can_recover'])
        with self.assertRaises(review.ActionConflict): self.prepare()
        self.assertEqual(CareerJobAnalysis.objects.get(pk=self.row.pk).extracted_payload,payload)

    def test_api_is_private_strict_session_csrf_and_roundtrips_retained_evidence(self):
        source=self.client.get(self.url)
        self.assertEqual(source.status_code, 200); self.assertIn('no-store', source['Cache-Control'])
        self.assertNotIn('resume', source.json())
        preview=self.client.post(self.url, {'mode':'preview','revision':source.json()['revision'],'fields':self.fields}, content_type='application/json')
        self.assertEqual(preview.status_code, 200)
        proposal=preview.json()
        response=self.client.post(self.url, {'mode':'confirm','proposal_id':proposal['proposal_id'],
            'fields':proposal['fields'],'confirmed':True}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        reopened=self.client.get(self.url).json()
        self.assertEqual(reopened['recoveries'][0]['previous_application'], self.source)
        self.assertEqual(self.client.get(self.url+'?owner=2').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'mode':'preview','owner':2}, content_type='application/json').status_code,400)
        csrf=Client(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.url, {'mode':'preview'}, content_type='application/json').status_code,403)
        self.client.logout(); self.assertEqual(self.client.get(self.url).status_code,403)


class ConcurrentCareerHistoryReviewTests(TransactionTestCase):
    def test_concurrent_confirmations_and_retry_keep_one_archive(self):
        owner=get_user_model().objects.create_user(username='synthetic-history-race')
        row=CareerJobAnalysis.objects.create(user=owner, extracted_payload={'application':{'stage':'applied'}})
        fields={'stage':'applied','on':timezone.localdate().isoformat()}
        proposal=review.prepare(owner,row.pk,review.inspect(owner,row.pk)['revision'],fields)
        barrier=Barrier(2, timeout=10)
        def call():
            try:
                barrier.wait()
                return review.confirm(owner,row.pk,proposal['proposal_id'],fields,True)
            except OperationalError: return None  # Shared-memory SQLite may reject a lock; the same card remains retryable.
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:call(), range(2)))
        self.assertTrue(any(isinstance(result,dict) for result in results),results)
        review.confirm(owner,row.pk,proposal['proposal_id'],fields,True)
        row.refresh_from_db()
        self.assertEqual(len(row.extracted_payload['application_history_recoveries']),1)
        self.assertEqual(OperationalLog.objects.get().payload['state'],'confirmed')
