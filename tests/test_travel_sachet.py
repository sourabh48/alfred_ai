"""NDMA SACHET official alerts before a trip (owner approved P1, 2026-11-25). Synthetic XML only; no network."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.mobility.models import TravelPlan
from apps.mobility.services.travel.proactive import next_steps
from apps.mobility.services.travel.providers import safety

# A square around Madikeri (Kodagu, Karnataka) and one far away in Kerala.
KODAGU = "12.3,75.6 12.3,75.9 12.6,75.9 12.6,75.6"
KOZHIKODE = "11.2,75.7 11.2,76.0 11.5,76.0 11.5,75.7"


def feed(*ids):
    items = "".join(f"<item><title>t</title><guid isPermaLink=\"false\">{i}</guid></item>" for i in ids)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><copyright>public domain</copyright>{items}</channel></rss>'


def cap(event="Heavy Rain", expires=None, status="Actual", msg="Alert", sender="KSDMA"):
    expires = (expires or timezone.now() + timedelta(hours=3)).isoformat()
    info = lambda lang, headline: (f"<cap:info><cap:language>{lang}</cap:language><cap:event>{event}</cap:event>"
                                   f"<cap:severity>Severe</cap:severity><cap:expires>{expires}</cap:expires>"
                                   f"<cap:headline>{headline}</cap:headline><cap:area><cap:areaDesc>Kodagu district</cap:areaDesc></cap:area></cap:info>")
    return (f'<cap:alert xmlns:cap="urn:oasis:names:tc:emergency:cap:1.2"><cap:sender>{sender}</cap:sender>'
            f"<cap:status>{status}</cap:status><cap:msgType>{msg}</cap:msgType>{info('kn', 'ಮಳೆ')}{info('en-IN', 'Heavy rain likely over Kodagu.')}</cap:alert>")


def polygon(points):
    return f"<alert><identifier>x</identifier><polygon>{points}</polygon></alert>"


class SachetTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        user = get_user_model().objects.create_user("synthetic-sachet", password="Test12345!")
        point = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [75.7412, 12.4244]},
                                                           "properties": {"name": "Coorg", "kind": "overnight"}}]}
        self.plan = TravelPlan.objects.create(user=user, title="Synthetic Coorg ride", destination="Coorg", status="planned",
                                              start_date=self.today + timedelta(days=1), end_date=self.today + timedelta(days=3),
                                              itinerary={"map": point})
        self.files, self.sent = {}, []
        for name, value in (("UsgsEarthquakes", {"quakes": []}), ("GoogleAirQuality", None)):
            stub = patch.object(getattr(safety, name), "fetch", side_effect=safety.ProviderError("network_error") if value is None else None,
                                return_value=(value, "h"))
            stub.start()
            self.addCleanup(stub.stop)

    def request(self, method, url, params=None, **kwargs):
        self.sent.append((url, params))
        key = url.rsplit("/", 1)[-1] + (f":{params['identifier']}" if params else "")
        body = self.files.get(key)
        if body is None:
            raise PublicHTTPError("api_error")
        return PublicResponse(body.encode(), "text/xml")

    def alerts(self):
        with patch.object(safety, "request", side_effect=self.request):
            return [s for s in next_steps(self.plan, self.today) if s["kind"] == "official_alert"]

    def test_current_alert_covering_the_destination_is_shown_and_others_are_not(self):
        self.files = {"rss_karnataka.xml": feed(1, 2, 3, 4, 5),
                      "FetchXMLFile:1": cap(), "FetchPolygonXMLFile:1": polygon(KODAGU),
                      "FetchXMLFile:2": cap(event="Thunderstorm"), "FetchPolygonXMLFile:2": polygon(KOZHIKODE),
                      "FetchXMLFile:3": cap(event="Old", expires=timezone.now() - timedelta(minutes=5)), "FetchPolygonXMLFile:3": polygon(KODAGU),
                      "FetchXMLFile:4": cap(event="Drill", status="Exercise"), "FetchPolygonXMLFile:4": polygon(KODAGU),
                      "FetchXMLFile:5": cap(event="Withdrawn", msg="Cancel"), "FetchPolygonXMLFile:5": polygon(KODAGU)}
        steps = self.alerts()
        self.assertEqual([s["title"] for s in steps], ["Severe alert: Heavy Rain at Coorg"])
        self.assertIn("Heavy rain likely over Kodagu. Area: Kodagu district. Valid until", steps[0]["detail"])  # English text chosen
        self.assertEqual(steps[0]["basis"], "NDMA SACHET, issued by KSDMA")
        self.assertEqual(steps[0]["links"], [{"label": "NDMA SACHET alerts", "url": "https://sachet.ndma.gov.in/"}])
        # Only the state name and alert identifiers leave the PC, never the coordinates.
        self.assertNotIn("12.4", repr(self.sent))
        self.assertNotIn("75.7", repr(self.sent))

    def test_state_without_a_feed_falls_back_to_the_national_feed(self):
        self.files = {"rss_india.xml": feed(7), "FetchXMLFile:7": cap(), "FetchPolygonXMLFile:7": polygon(KODAGU)}
        self.assertEqual(len(self.alerts()), 1)
        self.assertEqual([u.rsplit("/", 1)[-1] for u, _ in self.sent][:2], ["rss_karnataka.xml", "rss_india.xml"])

    def test_failed_or_hostile_feed_says_not_checked_never_none(self):
        self.files = {"rss_karnataka.xml": '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss>&a;</rss>'}
        steps = self.alerts()
        self.assertEqual([s["title"] for s in steps], ["Official warnings not checked"])
        self.assertIn("are unknown", steps[0]["detail"])

    def test_alert_without_an_area_is_reported_as_unplaced(self):
        self.files = {"rss_karnataka.xml": feed(9), "FetchXMLFile:9": cap()}
        steps = self.alerts()
        self.assertEqual(steps[0]["title"], "Official alerts in Karnataka to check")
        self.assertIn("1 current alert(s) had no map area", steps[0]["detail"])

    def test_cached_alert_that_has_since_expired_is_hidden(self):
        self.files = {"rss_karnataka.xml": feed(1), "FetchXMLFile:1": cap(expires=timezone.now() + timedelta(seconds=2)),
                      "FetchPolygonXMLFile:1": polygon(KODAGU)}
        self.assertEqual(len(self.alerts()), 1)
        with patch("apps.mobility.services.travel.proactive.timezone.now", return_value=timezone.now() + timedelta(minutes=1)):
            self.assertEqual(self.alerts(), [])  # served from the 30-minute cache, but the alert itself is over

    def test_trips_outside_india_make_no_sachet_call(self):
        self.plan.itinerary = {"map": {"features": [{"geometry": {"coordinates": [2.35, 48.86]}, "properties": {"kind": "overnight"}}]}}
        self.assertEqual(self.alerts(), [])
        self.assertEqual(self.sent, [])
