"""D2-A cross-action negative boundary and unmodified production quota checks."""
from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client, TestCase

from apps.mobility.models import TravelPlan, TravelPlanningSession
from apps.mobility.planner_views import PlannerWriteThrottle
from tests import test_travel_pdf_export as fixtures


class TravelSecurityTests(TestCase):
    ready=fixtures.TravelPDFExportTests.ready
    researched=fixtures.TravelPDFExportTests.researched
    set_stops=fixtures.TravelPDFExportTests.set_stops
    multi=fixtures.TravelPDFExportTests.multi

    def setUp(self):
        fixtures.TravelPDFExportTests.setUp(self)
        self.marker='SYNTHETIC PRIVATE TRIP D2'
        self.session.title=self.marker;self.session.save(update_fields=['title'])

    def targets(self):
        revision=self.session.revision
        actions=[dict(action='itinerary_edit',operation='undo',revision=revision,request_id=str(uuid4())),
                 dict(action='packing',operation='add',checklist_revision=0,item_id=str(uuid4()),label='D2 item'),
                 dict(action='reminders',operation='consent',reminder_revision=0,request_id=str(uuid4()),enabled=True),
                 dict(action='trip_documents',operation='list',revision=revision)]
        for kind in ('pdf','gpx','ics'):
            body=dict(action='export_'+kind,revision=revision)
            if kind=='ics':body['calendar']={'snapshot':'0'*64,'events':[]}
            actions.append(body)
        return [(self.url,body) for body in actions]+[(self.url+suffix+'/',{}) for suffix in ('affordability','savings')]

    def snapshot(self):
        return deepcopy((list(TravelPlan.objects.values()),list(TravelPlanningSession.objects.values())))

    def private_error(self,response,status):
        self.assertIn(response.status_code,status)
        self.assertEqual(response['Cache-Control'],'no-store, private')
        self.assertNotIn(self.marker.encode(),response.content)
        self.assertNotIn(b'Traceback',response.content)

    def test_all_actions_owner_authentication_csrf_and_private_errors(self):
        targets=self.targets();before=self.snapshot()
        self.client.force_login(self.other)
        for url,body in targets:self.private_error(self.client.post(url,body,content_type='application/json'),(404,))
        self.private_error(self.client.get(self.url),(404,))
        self.client.logout()
        for url,body in targets:self.private_error(self.client.post(url,body,content_type='application/json'),(401,403))
        self.private_error(self.client.get(self.url),(401,403))
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.user)
        for url,body in targets:self.private_error(csrf.post(url,body,content_type='application/json'),(403,))
        self.assertEqual(before,self.snapshot())
        # A real CSRF cookie/header admits the same packing endpoint.
        csrf.get('/mobility/')
        token=csrf.cookies[settings.CSRF_COOKIE_NAME].value
        url,body=targets[1]
        allowed=csrf.post(url,body,content_type='application/json',HTTP_X_CSRFTOKEN=token)
        self.assertEqual(allowed.status_code,200,allowed.content[:200])

    def test_revoked_server_session_rejects_every_action_without_mutation(self):
        targets=self.targets();before=self.snapshot()
        Session.objects.filter(session_key=self.client.session.session_key).delete()
        for url,body in targets:self.private_error(self.client.post(url,body,content_type='application/json'),(401,403))
        self.assertEqual(before,self.snapshot())

    def test_real_write_quota_is_enforced_without_clock_or_policy_overrides(self):
        before=self.snapshot()
        body=dict(action='calendar_preview',revision=self.session.revision)
        throttle=PlannerWriteThrottle()
        self.assertEqual(throttle.rate,'60/min')
        key=throttle.get_cache_key(SimpleNamespace(user=self.user),None)
        used=len(throttle.cache.get(key,[]))  # Setup's real stop-selection POST already consumed a slot.
        self.assertGreater(used,0);self.assertLess(used,throttle.num_requests)
        for _ in range(throttle.num_requests-used):
            response=self.client.post(self.url,body,content_type='application/json')
            self.assertEqual(response.status_code,200,response.content[:200])
        blocked=self.client.post(self.url,body,content_type='application/json')
        self.private_error(blocked,(429,));self.assertGreater(int(blocked['Retry-After']),0)
        self.assertEqual(self.client.get(self.url).status_code,200)
        self.client.force_login(self.other)
        self.private_error(self.client.post(self.url,body,content_type='application/json'),(404,))
        self.assertEqual(before,self.snapshot())
