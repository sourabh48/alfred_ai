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
