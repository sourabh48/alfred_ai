"""Owner-selected references reuse private copies without duplicating their bytes."""
from copy import deepcopy
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.ml_engine.services.document_corpus import DocumentCorpus
from apps.ml_engine.services.memory_key import MemoryStorageUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore
from apps.mobility.services.travel_conversation import new_session
from apps.mobility.services.travel_discovery import fact, candidates_for
from apps.mobility.services.travel_itinerary import build_itinerary
from apps.mobility.services.travel.editor import apply_edit
from tests import test_travel_planner as fixtures


class TravelDocumentTests(TestCase):
    def setUp(self):
        cache.clear(); self.addCleanup(cache.clear)
        fixtures.TravelPlannerTests.setUp(self)
        self.session=new_session(self.user)
        self.url=f'/api/mobility/planner/sessions/{self.session.pk}/'
        self.source=dict(id='a'*32,kind='upload',document_name='Synthetic itinerary <b>literal</b>.txt',
            source_fingerprint='1'*64,expires_at=(timezone.now()+timedelta(days=1)).isoformat())
        self.records={self.user.pk:[self.source],self.other.pk:[]}
        self.store_patch=patch('apps.mobility.services.travel.documents.MemoryStore')
        self.store_patch.start(); self.addCleanup(self.store_patch.stop)
        self.list_patch=patch('apps.mobility.services.travel.documents.DocumentCorpus.list',
            side_effect=lambda user:{'documents':self.records.get(user.pk,[])})
        self.listing=self.list_patch.start(); self.addCleanup(self.list_patch.stop)

    def update(self, operation, **changes):
        response=self.client.post(self.url,dict(action='trip_documents',operation=operation,
            revision=self.session.revision)|changes,content_type='application/json')
        self.session.refresh_from_db()
        return response

    def link(self, **changes):
        return self.update('link',**(dict(document_id=self.source['id'],fingerprint=self.source['source_fingerprint'])|changes))

    def test_empty_trip_does_not_open_private_store_and_responses_are_uncacheable(self):
        result=self.client.get(self.url)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['trip_documents'],[])
        self.listing.assert_not_called()
        self.assertIn('no-store',result['Cache-Control'])

    def test_link_is_idempotent_metadata_only_and_survives_saved_draft(self):
        listing=self.update('list')
        self.assertEqual(listing.status_code,200)
        self.assertNotIn('text',listing.json()['document_choices'][0])
        revision=self.session.revision
        self.assertEqual(self.link().status_code,200)
        new_revision=self.session.revision
        self.assertEqual(self.link(revision=revision).status_code,200)
        self.assertEqual(self.session.revision,new_revision)
        self.assertEqual(self.session.state['_itinerary_documents']['value'],[{'id':self.source['id'],'fingerprint':self.source['source_fingerprint']}])
        self.assertEqual(self.client.post(self.url,{'action':'save','draft':True,'revision':revision},content_type='application/json').status_code,409)
        self.assertEqual(self.client.post(self.url,{'action':'save','draft':True,'revision':new_revision},content_type='application/json').status_code,200)
        self.session.refresh_from_db(); self.session.plan.refresh_from_db()
        self.assertEqual(self.session.plan.planning_state['_itinerary_documents'],self.session.state['_itinerary_documents'])
        payload=self.client.get(self.url).json()
        self.assertNotIn('_itinerary_documents',payload['state'])
        self.assertEqual(payload['trip_documents'][0]['original_path'],f'/api/ai/document-corpus/{self.source["id"]}/original/')

    def test_foreign_missing_changed_sources_and_stale_writes_are_rejected(self):
        before=deepcopy(self.session.state)
        self.assertEqual(self.link(document_id='b'*32).status_code,409)
        self.assertEqual(self.link(fingerprint='2'*64).status_code,409)
        self.assertEqual(self.link(revision=self.session.revision+1).status_code,409)
        self.assertEqual(self.session.state,before)
        self.client.force_login(self.other)
        self.assertEqual(self.link().status_code,404)
        client=Client(enforce_csrf_checks=True); client.force_login(self.user)
        self.assertEqual(client.post(self.url,{'action':'trip_documents','operation':'list'}).status_code,403)

    def test_expired_or_changed_links_have_no_original_url_and_unlink_keeps_copy(self):
        self.assertEqual(self.link().status_code,200)
        self.source['source_fingerprint']='2'*64
        result=self.client.get(self.url).json()['trip_documents'][0]
        self.assertEqual(result['status'],'unavailable'); self.assertNotIn('original_path',result)
        self.source['expires_at']=(timezone.now()-timedelta(seconds=1)).isoformat()
        self.assertEqual(self.update('list').json()['document_choices'],[])
        linked_revision=self.session.revision
        self.assertEqual(self.update('unlink',document_id=self.source['id']).status_code,200)
        self.assertEqual(self.client.post(self.url,{'action':'save','draft':True,'revision':linked_revision},content_type='application/json').status_code,409)
        self.assertEqual(len(self.records[self.user.pk]),1)
        revision=self.session.revision
        self.assertEqual(self.update('unlink',document_id=self.source['id'],revision=revision-1).status_code,200)
        self.assertEqual(self.session.revision,revision)

    def test_private_store_outage_preserves_links_and_does_not_expose_exception_text(self):
        self.assertEqual(self.link().status_code,200)
        before=deepcopy(self.session.state)
        for error in (MemoryStorageUnavailable('Synthetic private key path must not escape'),RuntimeError('Synthetic protected key unavailable')):
            self.listing.side_effect=error
            result=self.update('list')
            self.assertEqual(result.status_code,503)
            self.assertNotIn('private key path',str(result.content))
            self.assertNotIn('protected key unavailable',str(result.content))
            self.assertEqual(self.session.state,before)
            self.assertEqual(self.client.get(self.url).json()['trip_documents'][0]['status'],'unavailable')
        self.assertEqual(self.update('unlink',document_id=self.source['id']).status_code,200)

    def test_linking_preserves_editor_undo_and_undo_preserves_document_reference(self):
        self.session.state.update(origin=fact('Bengaluru'),trip_duration=fact(3))
        candidate=candidates_for(self.user,self.session.state)[0]
        self.session.itinerary=build_itinerary(self.session.state,candidate); self.session.save()
        day=self.client.get(self.url).json()['itinerary']['days'][0]
        from uuid import uuid4
        apply_edit(self.session,dict(operation='add',revision=self.session.revision,request_id=str(uuid4()),
            day_id=day['id'],fields={'title':'Independent activity'}))
        self.assertEqual(self.link().status_code,200)
        self.assertTrue(self.client.get(self.url).json()['itinerary_editor']['can_undo'])
        apply_edit(self.session,dict(operation='undo',revision=self.session.revision,request_id=str(uuid4())))
        self.assertEqual(self.client.get(self.url).json()['trip_documents'][0]['status'],'available')

    def test_real_encrypted_original_remains_available_after_reference_unlink(self):
        self.store_patch.stop(); self.list_patch.stop()
        with TemporaryDirectory(prefix='alfred-trip-documents-') as directory, override_settings(ALFRED_MEMORY_DIR=directory), \
                patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=Mock(embed=Mock(side_effect=AssertionError('No model')))):
            corpus=DocumentCorpus(MemoryStore(directory))
            raw=b'Synthetic private travel reference. Not a booking confirmation.'
            saved=corpus.upload(self.user,SimpleUploadedFile('synthetic-trip.txt',raw,content_type='text/plain'),consent=True,days=1)
            source=saved['document']
            self.assertEqual(self.update('link',document_id=source['id'],fingerprint=source['source_fingerprint']).status_code,200)
            url=self.client.get(self.url).json()['trip_documents'][0]['original_path']
            result=self.client.get(url)
            self.assertEqual(result.status_code,200)
            self.assertTrue(result.streaming)
            self.assertEqual(b''.join(result.streaming_content),raw)
            self.assertEqual(self.update('unlink',document_id=source['id']).status_code,200)
            self.assertEqual(len(corpus.list(self.user)['documents']),1)
            result=self.client.get(url); self.assertEqual(result.status_code,200)
            self.assertTrue(result.streaming)
            self.assertEqual(b''.join(result.streaming_content),raw)
