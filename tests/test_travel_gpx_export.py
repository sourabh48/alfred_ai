"""Independent libxml parsing of saved-only GPX; synthetic locations, no network."""
from copy import deepcopy
from pathlib import Path

from django.test import Client, TestCase
from lxml import etree

from alfred_private_storage import private_directory
from apps.mobility.models import TravelPlan
from apps.mobility.services.travel_discovery import fact
from tests import test_travel_pdf_export as fixtures
from tests.test_travel_route_choices import route_fixture


class TravelGPXExportTests(TestCase):
    ready=fixtures.TravelPDFExportTests.ready
    researched=fixtures.TravelPDFExportTests.researched
    set_stops=fixtures.TravelPDFExportTests.set_stops
    multi=fixtures.TravelPDFExportTests.multi
    setUp=fixtures.TravelPDFExportTests.setUp

    def export(self, **fields):
        self.session.refresh_from_db()
        return self.client.post(self.url,dict(action='export_gpx',revision=self.session.revision)|fields,content_type='application/json')

    def parse(self,response):
        self.assertEqual(response.status_code,200,response.content[:500])
        self.assertEqual(response['Content-Type'],'application/gpx+xml')
        root=etree.fromstring(response.content,etree.XMLParser(resolve_entities=False,no_network=True))
        self.assertEqual(root.tag,'{http://www.topografix.com/GPX/1/1}gpx')
        self.assertEqual(dict(root.attrib),dict(version='1.1',creator='ALFRED'))
        self.assertFalse(root.xpath('//*[local-name()="trk"]'))
        return root

    def names(self,root):
        return root.xpath('g:wpt/g:name/text()',namespaces={'g':root.nsmap[None]})

    def plan(self):
        return TravelPlan.objects.get(pk=self.session.plan_id)

    def test_multistop_order_source_private_headers_and_no_inferred_roads(self):
        plan=self.plan();before=deepcopy(plan.planning_state)
        response=self.export();root=self.parse(response)
        self.assertEqual(self.names(root),[s['name'] for s in plan.itinerary['stops']])
        self.assertEqual([etree.QName(n).localname for n in root],['metadata','wpt','wpt'])
        self.assertIn(b'Waypoints only',response.content)
        self.assertIn(b'not road navigation',response.content)
        self.assertEqual(response['Content-Disposition'],'attachment; filename="alfred-itinerary.gpx"')
        for key,val in [('Cache-Control','no-store, private'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer')]:self.assertEqual(response[key],val)
        self.assertTrue(root.xpath('//*[local-name()="src"]'))
        plan.refresh_from_db();self.assertEqual(plan.planning_state,before)
        out=private_directory(Path(__file__).resolve().parents[1]/'artifacts/travel-gpx-20261027')
        (out/'synthetic-waypoints.gpx').write_bytes(response.content)

    def test_coordinate_zero_negative_precision_and_invalid_partial_locations(self):
        plan=self.plan();stops=plan.planning_state['_itinerary_stops']['value']
        stops[0].update(lat='0',lon='-0');stops[1].update(lat='-89.123456789',lon='179.987654321')
        plan.save(update_fields=['planning_state'])
        root=self.parse(self.export());points=root.xpath('//*[local-name()="wpt"]')
        self.assertEqual(dict(points[0].attrib),dict(lat='0',lon='0'))
        self.assertEqual(dict(points[1].attrib),dict(lat='-89.123456789',lon='179.987654321'))
        for latitude,longitude in [(None,2),(True,2),('NaN',2),(91,2),(-91,2),(0,180),(0,-181),([],2),('1e999999',2)]:
            stops[0].update(lat=latitude,lon=longitude);plan.save(update_fields=['planning_state'])
            response=self.export();self.assertEqual(len(self.parse(response).xpath('//*[local-name()="wpt"]')),1)
            self.assertIn(b'1 stops omitted',response.content)

    def test_empty_malformed_and_bounded_input_fail_without_partial_xml(self):
        plan=self.plan()
        for state,itinerary in [({},{}),({'selected_location':fact({'name':'x','lat':None,'lon':None})},{'destination':'x'}),
            ({},{'map':{'features':[{}]*101}}),({},{'map':{'features':[dict(properties=dict(name='x',kind='overnight'),geometry=dict(type='Point',coordinates=[]))]},'destination':'x'}),
            ({},{'stops':[{}]*6})]:
            plan.planning_state=state;plan.itinerary=itinerary;plan.save(update_fields=['planning_state','itinerary'])
            response=self.export();self.assertEqual(response.status_code,400)
            self.assertNotIn(b'<gpx',response.content)

    def test_xml_escaping_controls_and_unrelated_private_data_exclusion(self):
        plan=self.plan();stops=plan.planning_state['_itinerary_stops']['value']
        title='Café <location> & "private"'
        plan.itinerary['stops'][0]['name']=title;stops[0]['name']=title
        stops[0]['source']='https://example.invalid/source?private=NOT_FOR_GPX_SECRET'
        plan.planning_state['private_note']=fact('NOT_FOR_GPX_PRIVATE_NOTE')
        plan.save(update_fields=['itinerary','planning_state'])
        response=self.export();root=self.parse(response)
        self.assertEqual(self.names(root)[0],title)
        self.assertNotIn(b'NOT_FOR_GPX',response.content)
        self.assertNotIn(b'<!DOCTYPE',response.content)
        plan.title='bad\x01title';plan.save(update_fields=['title'])
        self.assertEqual(self.export().status_code,400)

    def single_route(self):
        plan=self.plan();result=route_fixture().as_dict();result['response_hash']='a'*64
        result['request_parameters']=dict(start=[77.59,12.97],end=['77.030000','12.18000'])
        name='Synthetic destination';point=dict(name=name,lat=12.18,lon=77.03)
        plan.planning_state={'selected_location':fact(point)}
        plan.itinerary={'destination':name,'route_result':result,'route':dict(confidence='LIKELY',selected_route_id=result['payload']['routes'][0]['route_id'])}
        plan.save(update_fields=['planning_state','itinerary'])
        return plan

    def test_only_selected_fresh_source_backed_provider_line_preserves_axis_and_order(self):
        self.single_route();response=self.export();root=self.parse(response)
        points=root.xpath('//*[local-name()="rtept"]')
        self.assertEqual([dict(p.attrib) for p in points],[dict(lat='12.97',lon='77.59'),dict(lat='12.18',lon='77.03')])
        self.assertIn(b'not a recorded track or a verified motorcycle route',response.content)
        self.assertEqual(len(root.xpath('//*[local-name()="link"]')),1)
        out=private_directory(Path(__file__).resolve().parents[1]/'artifacts/travel-gpx-20261027')
        (out/'synthetic-route.gpx').write_bytes(response.content)

    def test_stale_unknown_wrong_source_unsupported_and_invalid_geometry_are_waypoints_only(self):
        plan=self.single_route();original=deepcopy(plan.itinerary)
        for key,val in [('expires_at','2000-01-01T00:00:00+00:00'),('retrieved_at','2099-01-01T00:00:00+00:00'),('confidence','UNKNOWN'),('stale',True),('response_hash',''),('provider','unknown'),('success',False)]:
            plan.itinerary=deepcopy(original);plan.itinerary['route_result'][key]=val;plan.save(update_fields=['itinerary'])
            root=self.parse(self.export());self.assertFalse(root.xpath('//*[local-name()="rte"]'))
        for geometry in [dict(type='Polygon',coordinates=[]),dict(type='LineString',coordinates=[[77,12],[999,12]]),dict(type='LineString',coordinates=[[77,12,1],[78,13,2]]),dict(type='LineString',coordinates=[[77,12]]*5001)]:
            plan.itinerary=deepcopy(original);plan.itinerary['route_result']['payload']['routes'][0]['geometry']=geometry;plan.save(update_fields=['itinerary'])
            self.assertFalse(self.parse(self.export()).xpath('//*[local-name()="rte"]'))

    def test_saved_only_auth_owner_csrf_revision_and_extra_field_protection(self):
        self.session.state={};self.session.itinerary={};self.session.save(update_fields=['state','itinerary'])
        self.parse(self.export())
        self.assertEqual(self.export(revision=self.session.revision+1).status_code,409)
        self.assertEqual(self.export(include_private=True).status_code,400)
        self.client.force_login(self.other);self.assertEqual(self.export().status_code,404)
        self.client.logout();self.assertIn(self.export().status_code,(401,403))
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post(self.url,dict(action='export_gpx',revision=0),content_type='application/json').status_code,403)

    def test_destination_only_selected_location_and_saved_map_fallback(self):
        plan=self.single_route();plan.itinerary['route_result']={};plan.save(update_fields=['itinerary'])
        self.assertEqual(self.names(self.parse(self.export())),['Synthetic destination'])
        plan.planning_state={}
        plan.itinerary['map']={'features':[dict(properties=dict(name='Synthetic destination',kind='overnight'),geometry=dict(type='Point',coordinates=[77.03,12.18]))]}
        plan.save(update_fields=['planning_state','itinerary'])
        self.assertEqual(self.names(self.parse(self.export())),['Synthetic destination'])

    def test_expired_waypoint_discovery_and_map_metadata_are_dated_cached_unknown(self):
        plan=self.plan()
        source=dict(freshness='LIVE',confidence='VERIFIED',retrieved_at='1999-12-31T00:00:00+00:00',expires_at='2000-01-01T00:00:00+00:00')
        point=plan.planning_state['_itinerary_stops']['value'][0]
        point.update(source_freshness='RECENTLY_VERIFIED',discovery_result=dict(source))
        plan.save(update_fields=['planning_state']);saved=deepcopy(plan.planning_state)
        root=self.parse(self.export());text=etree.tostring(root[1]).decode()
        for expected in ('CACHED','UNKNOWN','1999-12-31','2000-01-01'):self.assertIn(expected,text)
        self.assertNotIn('RECENTLY_VERIFIED',text)
        plan.refresh_from_db();self.assertEqual(plan.planning_state,saved)
        plan.planning_state={}
        plan.itinerary={'destination':'Synthetic stop','map':{'features':[dict(properties=dict(source,name='Synthetic stop',kind='overnight'),geometry=dict(type='Point',coordinates=[77,12]))]}}
        plan.save(update_fields=['planning_state','itinerary'])
        text=etree.tostring(self.parse(self.export())[1]).decode()
        for expected in ('CACHED','UNKNOWN','1999-12-31','2000-01-01'):self.assertIn(expected,text)
