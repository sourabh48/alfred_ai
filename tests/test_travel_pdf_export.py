"""Independent parsing of owner-requested, saved-only itinerary PDFs."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase
from pypdf import PdfReader

from alfred_private_storage import private_directory
from apps.mobility.models import TravelPlan
from apps.mobility.services.travel_conversation import save_plan
from tests import test_travel_multistop as fixtures


class TravelPDFExportTests(TestCase):
    ready=fixtures.TravelMultiStopTests.ready
    researched=fixtures.TravelMultiStopTests.researched
    set_stops=fixtures.TravelMultiStopTests.set_stops
    multi=fixtures.TravelMultiStopTests.multi

    def setUp(self):
        cache.clear();self.addCleanup(cache.clear)
        fixtures.TravelMultiStopTests.setUp(self)
        self.session,_=self.multi()
        save_plan(self.session,draft=True);self.session.refresh_from_db()
        self.url=f'/api/mobility/planner/sessions/{self.session.pk}/'

    def export(self, **fields):
        self.session.refresh_from_db()
        return self.client.post(self.url,dict(action='export_pdf',revision=self.session.revision)|fields,content_type='application/json')

    def parse(self,response):
        self.assertEqual(response.status_code,200,response.content[:500])
        self.assertEqual(response['Content-Type'],'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        reader=PdfReader(BytesIO(response.content),strict=True)
        self.assertTrue(reader.pages)
        return reader,'\n'.join(page.extract_text() for page in reader.pages)

    def test_explicit_pdf_preserves_saved_order_has_private_headers_and_no_active_content(self):
        response=self.export();reader,text=self.parse(response)
        self.assertEqual(response['Cache-Control'],'no-store, private')
        self.assertEqual(response['Content-Disposition'],'attachment; filename="alfred-itinerary.pdf"')
        self.assertEqual(response['X-Content-Type-Options'],'nosniff')
        self.assertEqual(response['Referrer-Policy'],'no-referrer')
        self.assertIn('PRIVATE SAVED ITINERARY',text)
        self.assertIn('not proof of a booking',text)
        self.assertLess(text.index('Day 1:'),text.index('Day 2:'))
        self.assertIn(self.session.itinerary['days'][0]['items'][0]['title'],text)
        self.assertNotIn('/OpenAction',reader.trailer['/Root'])
        self.assertNotIn('/AA',reader.trailer['/Root'])
        self.assertNotIn('/Names',reader.trailer['/Root'])
        self.assertTrue(all(not page.get('/Annots') for page in reader.pages))
        self.assertEqual(reader.metadata.author,'ALFRED')

    def test_auth_owner_csrf_stale_revision_and_extra_fields_fail_closed(self):
        self.assertEqual(self.export(revision=self.session.revision+1).status_code,409)
        self.assertEqual(self.export(include_private=True).status_code,400)
        self.assertEqual(self.client.get(self.url)['Content-Type'],'application/json')
        self.client.force_login(self.other);self.assertEqual(self.export().status_code,404)
        self.client.logout();self.assertIn(self.export().status_code,(401,403))
        secured=Client(enforce_csrf_checks=True);secured.force_login(self.user)
        self.assertEqual(secured.post(self.url,dict(action='export_pdf',revision=0),content_type='application/json').status_code,403)

    def test_only_saved_itinerary_exports_and_unrelated_private_state_is_excluded(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        original=deepcopy(plan.itinerary)
        plan.planning_state['private_export_sentinel']={'value':'NOT_FOR_EXPORT_PRIVATE_RECORD'}
        plan.itinerary['owner_note']='NOT_FOR_EXPORT_UNRELATED_NOTE'
        plan.itinerary['budget']['expected']='987654321.99'
        plan.save(update_fields=['planning_state','itinerary'])
        before=deepcopy(plan.planning_state)
        self.session.itinerary['days'][0]['items'][0]['title']='NOT_SAVED_ACTIVITY'
        self.session.save(update_fields=['itinerary'])
        with patch('apps.mobility.services.travel.documents.MemoryStore',side_effect=AssertionError('Export must not open private corpus')):
            _,text=self.parse(self.export())
        for hidden in ('NOT_FOR_EXPORT_PRIVATE_RECORD','NOT_FOR_EXPORT_UNRELATED_NOTE','NOT_SAVED_ACTIVITY','987654321.99'):
            self.assertNotIn(hidden,text)
        self.assertIn(original['days'][0]['items'][0]['title'],text)
        plan.refresh_from_db();self.assertEqual(plan.planning_state,before)

    def test_expired_source_snapshot_is_dated_and_unknown_without_live_checks(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        plan.itinerary['sources']=[dict(source_name='Synthetic weather source',data_type='weather',status='ok',freshness='LIVE',confidence='VERIFIED',retrieved_at='1999-12-31T00:00:00+00:00',valid_until='2000-01-01T00:00:00+00:00')]
        plan.save(update_fields=['itinerary'])
        _,text=self.parse(self.export())
        self.assertIn('Synthetic weather source',text);self.assertIn('UNKNOWN',text);self.assertIn('CACHED',text)
        self.assertIn('2000-01-01',text)
        self.assertNotIn('confidence: VERIFIED',text)

    def test_malformed_missing_and_oversized_saved_data_returns_no_partial_pdf(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        for itinerary in ({},{'days':[{}]*61},{'days':[dict(title='x'*2401,items=[])]},{'days':[dict(items='invalid')]}):
            with self.subTest(itinerary_type=type(itinerary).__name__):
                plan.itinerary=itinerary;plan.save(update_fields=['itinerary'])
                response=self.export();self.assertEqual(response.status_code,400)
                self.assertFalse(response.content.startswith(b'%PDF'))

    def test_multistop_sources_keep_location_dates_and_unknowns_with_shared_bounds(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        self.assertEqual(plan.itinerary['sources'],[])
        stop=plan.itinerary['stops'][0]
        stop['sources']=[dict(source_name='Synthetic stop permit',data_type='permits',
            confidence='VERIFIED',freshness='LIVE',retrieved_at='1999-12-31T00:00:00+00:00',expires_at='2000-01-01T00:00:00+00:00')]
        plan.save(update_fields=['itinerary'])
        _,text=self.parse(self.export())
        for expected in (stop['name'],'Synthetic stop permit','1999-12-31','2000-01-01','UNKNOWN','CACHED'):
            self.assertIn(expected,text)
        self.assertNotIn('No route, weather, place or restriction source metadata',text)
        self.assertNotIn('confidence: VERIFIED',text)
        for bad in ('malformed',[None],stop['sources']*101):
            stop['sources']=bad
            plan.save(update_fields=['itinerary'])
            response=self.export()
            self.assertEqual(response.status_code,400)
            self.assertFalse(response.content.startswith(b'%PDF'))

    def test_unicode_escaped_markup_and_multiple_pages_render_without_clipping(self):
        import fitz
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        plan.title='Synthetic café यात्रा itinerary'
        day=deepcopy(plan.itinerary['days'][0])
        day['items']=[dict(title="<img src='https://example.invalid/tracker'> Synthetic café visit "+str(i),period='Morning',duration='45 minutes') for i in range(20)]
        day['items'][-1]['title']='X'*240
        plan.itinerary['days']=[deepcopy(day) for _ in range(6)]
        plan.save(update_fields=['title','itinerary'])
        response=self.export();reader,text=self.parse(response)
        self.assertGreater(len(reader.pages),1)
        self.assertIn('café',text);self.assertIn('<img',text)
        output=private_directory(Path(__file__).resolve().parents[1]/'artifacts/travel-export-20261027/preview')
        (output/'itinerary.pdf').write_bytes(response.content)
        with fitz.open(stream=response.content,filetype='pdf') as document:
            self.assertEqual(sum(page.get_text().count('X') for page in document),240*6)
            for page in document:
                self.assertFalse(page.get_images())
                for block in page.get_text('blocks'):
                    self.assertGreaterEqual(block[0],35);self.assertLessEqual(block[2],page.rect.width-30)
                    self.assertLessEqual(block[3],page.rect.height-20)
            document[0].get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(output/'first-page.png')
            document[-1].get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(output/'last-page.png')

    def test_renderer_outage_is_sanitized_and_does_not_mutate_saved_trip(self):
        before=TravelPlan.objects.get(pk=self.session.plan_id).itinerary
        with patch('fitz.Story',side_effect=RuntimeError('NOT_FOR_EXPORT_SERVER_PATH')):
            response=self.export()
        self.assertEqual(response.status_code,503)
        self.assertNotIn('NOT_FOR_EXPORT_SERVER_PATH',response.content.decode())
        self.assertEqual(TravelPlan.objects.get(pk=self.session.plan_id).itinerary,before)

    def test_page_limit_rejects_large_valid_structure_without_partial_download(self):
        plan=TravelPlan.objects.get(pk=self.session.plan_id)
        item=dict(title='Visit',period='AM',duration='1h')
        plan.itinerary['days']=[dict(title='Synthetic bounded export',items=[dict(item) for _ in range(20)]) for _ in range(60)]
        plan.save(update_fields=['itinerary'])
        response=self.export()
        self.assertEqual(response.status_code,400)
        self.assertIn('40-page',response.content.decode())
        self.assertFalse(response.content.startswith(b'%PDF'))
