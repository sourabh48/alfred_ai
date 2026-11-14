"""The Skyscanner search link needs both airport codes and sends only codes, dates and a traveller count."""
from urllib.parse import urlsplit

from django.test import SimpleTestCase

from apps.mobility.services.travel.links import external_links
from apps.mobility.services.travel_discovery import fact


class SkyscannerLinkTests(SimpleTestCase):
    def setUp(self):
        self.state = {k: fact(v) for k, v in {"origin": "Bengaluru", "trip_duration": 3, "budget": 15000,
            "available_start_date": "2026-10-02", "available_end_date": "2026-10-05", "number_of_travelers": 2}.items()}

    def test_skyscanner_link_needs_both_airports_and_names_what_it_sends(self):
        def skyscanner(**extra):
            state = {**self.state, **{k: fact(v) for k, v in extra.items()}}
            return [x for x in external_links(state, {"name": "Kochi"}) if "skyscanner" in x["url"]]
        self.assertEqual(skyscanner(), [], "no link without airport codes")
        self.assertEqual(skyscanner(origin_airport="BLR"), [])
        self.assertEqual(skyscanner(origin_airport="BLR", destination_airport="blr"), [], "same airport")
        self.assertEqual(skyscanner(origin_airport="Bengaluru", destination_airport="COK"), [], "not a code")
        [link] = skyscanner(origin_airport="blr", destination_airport="COK")
        self.assertEqual(link["category"], "flights")
        self.assertEqual(link["label"], "Search Skyscanner with your airports, traveller count and dates")
        self.assertEqual(link["url"], "https://www.skyscanner.co.in/transport/flights/blr/cok/261002/261005/?adultsv2=2")
        for private in ("Bengaluru", "15000"):
            self.assertNotIn(private, link["url"])
        [undated] = skyscanner(origin_airport="BLR", destination_airport="COK", available_start_date="", available_end_date="",
                               number_of_travelers=20)
        self.assertEqual(undated["label"], "Search Skyscanner with your airports and traveller count")
        self.assertEqual(undated["url"], "https://www.skyscanner.co.in/transport/flights/blr/cok/?adultsv2=8")
        [one_way] = skyscanner(origin_airport="BLR", destination_airport="COK", available_end_date="2026-09-01")
        self.assertEqual(urlsplit(one_way["url"]).path, "/transport/flights/blr/cok/261002/", "a return before departure is dropped")
