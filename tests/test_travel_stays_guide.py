"""Wikivoyage Sleep listings: guide leads with contributor price text, never live rates; only the place name leaves."""
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.mobility.services.travel.providers.base import ProviderError
from apps.mobility.services.travel.providers.web import WikivoyageStays, sleep_listings
from apps.mobility.services.travel.research import quality_contract
from apps.mobility.services.travel.providers.base import ProviderResult

ARTICLE = """Intro text.
==Sleep==
===Budget===
* {{sleep | name=Synthetic Hostel | url=https://hostel.example.org/ | phone=+91 98 7654 3210 ext<script> | price=₹800 per bed {{nowrap|incl. tax}} | checkin=noon | checkout=10AM | lat=32.24 | long=77.19 | content=Near the [[Mall Road|mall]], '''quiet''' rooms. | lastedit=2025-04-01 }}
* {{sleep | name=Plain Http Inn | url=http://inn.example.org/rooms | price= | lat= | long= }}
===Splurge===
* {{listing | type=sleep | name=Synthetic Resort | url=javascript:alert(1) | lat=999 | long=77 | price=₹9000 }}
* {{listing | type=eat | name=Not A Hotel }}
* {{sleep | url=https://nameless.example.org/ }}
* {{sleep | name=Unclosed
==Eat==
* {{eat | name=Synthetic Cafe }}
"""


class StaysGuideTests(SimpleTestCase):
    def test_sleep_listings_are_parsed_cleaned_and_bounded(self):
        rows = sleep_listings(ARTICLE)
        self.assertEqual([r["name"] for r in rows], ["Synthetic Hostel", "Plain Http Inn", "Synthetic Resort"])
        hostel, inn, resort = rows
        self.assertEqual((hostel["tier"], resort["tier"]), ("Budget", "Splurge"))
        self.assertEqual(hostel["price_text"], "₹800 per bed")  # free text, not parsed into money
        self.assertEqual(hostel["description"], "Near the mall, quiet rooms.")
        self.assertEqual(hostel["phone"], "+91 98 7654 3210")
        self.assertEqual((hostel["lat"], hostel["lon"], hostel["check_in"]), (32.24, 77.19, "noon"))
        self.assertEqual((inn["website"], inn["website_host"], inn["lat"]), ("", "inn.example.org", None))
        self.assertEqual((resort["website"], resort["website_host"], resort["lat"]), ("", "", None))
        self.assertTrue(all(r["availability"] == "UNKNOWN" for r in rows))
        self.assertEqual(sleep_listings("No sleep section"), [])
        self.assertEqual(len(sleep_listings("==Sleep==\n" + "* {{sleep|name=X}}\n" * 50)), 30)

    def test_only_the_place_name_is_sent_and_the_response_is_normalized(self):
        provider = WikivoyageStays()
        params = provider.parameters({"destination": "  Manali ", "budget": 50000, "check_in": "2026-12-01"})
        self.assertEqual(params, {"destination": "Manali"})
        for bad in ("", "A|B", "{{x}}", "[[x]]"):
            with self.assertRaises(ProviderError):
                provider.parameters({"destination": bad})
        with patch("apps.mobility.services.travel.providers.web.request_json") as request:
            provider.fetch(params)
        sent = request.call_args.kwargs["params"]
        self.assertEqual(sent["titles"], "Manali")
        self.assertNotIn("budget", str(request.call_args))
        raw = {"query": {"pages": [{"pageid": 7, "title": "Manali", "revisions": [
            {"timestamp": "2026-11-09T03:26:28Z", "slots": {"main": {"content": ARTICLE}}}]}]}}
        result = provider.normalize(raw, params)
        self.assertEqual(result["article"], "Manali")
        self.assertEqual(result["options"][0]["source_url"], "https://en.wikivoyage.org/wiki/Manali#Sleep")
        self.assertEqual(result["options"][0]["id"], "wikivoyage-stay:7:0")
        self.assertEqual(provider.normalize({"query": {"pages": [{"title": "Nowhere", "missing": True}]}}, params)["options"], [])
        with self.assertRaises(ProviderError):
            provider.normalize({"error": {"code": "maxlag"}}, params)

    def test_guide_listings_count_as_leads_not_verified_results(self):
        contract = quality_contract([ProviderResult("wikivoyage", "stays_guide", success=True, status="ok", freshness="LIVE", payload={})])
        self.assertNotIn("stays_guide", contract["verified"])
        self.assertIn("stays_guide", contract["research_leads"])


from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.mobility.models import TravelPlanningSession, TravelProviderRequest
from apps.mobility.services.travel.providers.web import HotelWebsite, lodging_details, robots_allows

HOTEL_PAGE = """<html><head><script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"WebSite","name":"Not lodging"},
 {"@type":["Hotel","LocalBusiness"],"name":"Synthetic <b>Lodge</b>","telephone":"+91 98 7654 3210<script>",
  "address":{"@type":"PostalAddress","streetAddress":"1 Hill Road","addressLocality":"Manali","addressCountry":{"name":"IN"}},
  "checkinTime":"14:00","checkoutTime":"11:00","priceRange":"₹₹","starRating":{"ratingValue":"3"},
  "aggregateRating":{"ratingValue":"4.4","reviewCount":"120"},"petsAllowed":false,
  "amenityFeature":[{"@type":"LocationFeatureSpecification","name":"Parking","value":true},
                    {"@type":"LocationFeatureSpecification","name":"Pool","value":false},"Wifi"],
  "geo":{"latitude":"32.2","longitude":"999"}}]}</script>
<script type="application/ld+json">{ broken</script></head></html>"""


class HotelWebsiteParserTests(SimpleTestCase):
    def test_reads_only_lodging_schema_and_cleans_values(self):
        details = lodging_details(HOTEL_PAGE)
        self.assertEqual(details["name"], "Synthetic Lodge")
        self.assertEqual(details["phone"], "+91 98 7654 3210")
        self.assertEqual(details["address"], "1 Hill Road, Manali, IN")
        self.assertEqual(details["amenities"], ["Parking", "Wifi"])
        self.assertEqual((details["pets_allowed"], details["star_rating"], details["review_count"]), ("No", "3", "120"))
        self.assertEqual(details["lat"], 32.2)
        self.assertNotIn("lon", details)
        self.assertEqual(lodging_details('<script type="application/ld+json">{"@type":"Restaurant","name":"x"}</script>'), {})
        self.assertEqual(lodging_details('<meta name="description" content="Cosy <b>rooms</b>  by the river">'), {"page_summary": "Cosy rooms by the river"})

    def test_robots_rules(self):
        url = "https://stay.example.org/rooms"
        self.assertFalse(robots_allows(url, lambda u: (200, "User-agent: *\nDisallow: /rooms")))
        self.assertTrue(robots_allows(url, lambda u: (200, "User-agent: OtherBot\nDisallow: /")))
        self.assertFalse(robots_allows(url, lambda u: (200, "User-agent: ALFRED-travel\nDisallow: /")))
        self.assertTrue(robots_allows(url, lambda u: (404, "")))

    def test_disallowed_site_is_never_opened(self):
        provider = HotelWebsite("https://stay.example.org/")
        robots = type("R", (), {"status": 200, "content": b"User-agent: *\nDisallow: /", "content_type": "text/plain"})
        with patch.object(HotelWebsite, "_get", return_value=robots) as get:
            with self.assertRaises(ProviderError) as raised:
                provider.fetch({"url": "https://stay.example.org/"})
        self.assertEqual(raised.exception.code, "robots_disallowed")
        self.assertEqual([c.args[0] for c in get.call_args_list], ["https://stay.example.org/robots.txt"])

    def test_only_its_own_url_is_accepted(self):
        with self.assertRaises(ProviderError):
            HotelWebsite("https://stay.example.org/").parameters({"url": "https://other.example.org/"})


class StayDetailsEndpointTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_user("stayowner", password="synthetic-pass-1")
        self.other = users.create_user("stayother", password="synthetic-pass-2")
        option = {"name": "Synthetic Lodge", "website": "https://stay.example.org/"}
        self.session = TravelPlanningSession.objects.create(user=self.owner, title="Synthetic trip",
            candidates=[{"name": "Manali", "stays_guide_result": {"payload": {"options": [option]}}}])
        self.client = APIClient()
        self.url = f"/api/mobility/planner/sessions/{self.session.pk}/stay-details/"

    def test_reads_a_listed_site_for_its_owner_only(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post(self.url, {"url": "https://evil.example.org/"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url, {"url": "http://stay.example.org/"}, format="json").status_code, 400)
        with patch.object(HotelWebsite, "fetch", return_value=(HOTEL_PAGE, "hash")) as fetch:
            response = self.client.post(self.url, {"url": "https://stay.example.org/"}, format="json")
            again = self.client.post(self.url, {"url": "https://stay.example.org/"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payload"]["details"]["name"], "Synthetic Lodge")
        self.assertTrue(again.json()["cached"])
        fetch.assert_called_once()
        self.assertEqual(TravelProviderRequest.objects.filter(provider="hotel_website", network_call=True).count(), 1)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(self.url, {"url": "https://stay.example.org/"}, format="json").status_code, 404)
