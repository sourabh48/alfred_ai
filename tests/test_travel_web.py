from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.mobility.services.travel.providers.base import ProviderResult
from alfred_ai.services.public_http import normalized_link
from apps.mobility.services.travel.providers.places import OverpassPlaces
from apps.mobility.services.travel.providers.web import BraveSearch, SearXNGSearch, WikivoyageDestinations, WikivoyageSearch, source_type
from apps.mobility.services.travel.research import research_candidates, quality_contract
from apps.mobility.services.travel.links import BOOKING_SITES, booking_sites, external_links
from apps.mobility.services.travel.discovery import remember
from apps.mobility.services.travel_conversation import new_session
from apps.mobility.services.travel_discovery import fact


class TravelWebTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("web-traveller",email="private@example.org")
        self.state = {k:fact(v) for k,v in {"origin":"Bengaluru","trip_duration":3,"budget":15000,
            "available_start_date":"2026-10-02","available_end_date":"2026-10-05","number_of_travelers":2}.items()}

    def test_web_queries_use_public_slots_and_drop_private_fields(self):
        provider = BraveSearch()
        p = provider.parameters({"origin":"Bengaluru","destination":"Coorg","topic":"closures","date":"2026-10-02",
            "email":self.user.email,"budget":15000,"message":"My account is confidential","registration":"KA01XX1234"})
        query = provider.search_query(p)
        self.assertIn("Bengaluru to Coorg",query)
        self.assertIn("2026-10",query)
        self.assertNotIn("private",str(p))
        self.assertNotIn("15000",str(p))
        p = provider.parameters({"origin":"My family private@example.org","destination":"Coorg","topic":"permits"})
        self.assertEqual(p["origin"],"")

    def test_source_priority_is_not_rule_verification(self):
        provider = BraveSearch()
        p = provider.parameters({"destination":"Coorg","topic":"permits"})
        result = provider.normalize({"web":{"results":[
            {"url":"https://blog.example/article","title":"Open every day"},
            {"url":"https://forest.kerala.gov.in/advisory","title":"Official notice"},
            {"url":"javascript:alert(1)","title":"unsafe"},
            {"url":"https://forest.kerala.gov.in/advisory","title":"duplicate"}]}},p)
        self.assertEqual(len(result["findings"]),2)
        first = result["findings"][0]
        self.assertEqual(first["source_type"],"official_authority")
        self.assertEqual(first["rule_status"],"unverified")
        self.assertEqual(first["availability"],"UNKNOWN")
        self.assertEqual(source_type("https://forest.gov.in.evil.example/")[0],"general_web")
        self.assertEqual(quality_contract([ProviderResult("brave","web",success=True,status="ok",payload=result)])["verified"],[])

    @patch.dict("os.environ", {"TRAVEL_BRAVE_API_KEY":"fixture","TRAVEL_BRAVE_STORAGE_ALLOWED":"false"})
    def test_storage_rights_are_required_before_search(self):
        self.assertIn("storage_rights",BraveSearch().unavailable_reason())

    def test_wiki_normalization_deduplicates_and_rejects_non_places(self):
        raw = {"query":{"pages":[{"pageid":42,"ns":0,"title":"Talakadu","coordinates":[{"lat":12.18,"lon":77.03}]},
            {"pageid":43,"ns":0,"title":"Talakadu","coordinates":[{"lat":12.18,"lon":77.03}]},
            {"pageid":44,"ns":0,"title":"Packing list"}]}}
        result = WikivoyageDestinations().normalize(raw,{})
        self.assertEqual(len(result["destinations"]),1)
        self.assertEqual(result["destinations"][0]["name"],"Talakadu")
        self.assertEqual(result["destinations"][0]["popularity"],"UNKNOWN")

    @patch("apps.mobility.services.travel.research.query")
    def test_dynamic_destination_outside_seed_catalog_and_visited_suppression(self, query):
        raw = {"query":{"pages":[{"pageid":42,"ns":0,"title":"Talakadu","coordinates":[{"lat":12.18,"lon":77.03}]}]}}
        result = ProviderResult("wikivoyage","destinations",success=True,status="ok",freshness="LIVE",payload=WikivoyageDestinations().normalize(raw,{}))
        query.return_value = result
        options = research_candidates(self.user,self.state,[])
        self.assertEqual(options[0]["name"],"Talakadu")
        self.assertEqual(options[0]["discovery_result"]["provider"],"wikivoyage")
        remember(self.user,options[0],"visited")
        self.assertEqual(research_candidates(self.user,{**self.state,"only_new_places":fact(True)},[]),[])

    @patch("apps.mobility.services.travel.research.query")
    def test_failed_discovery_retains_offline_options_with_reason(self, query):
        query.return_value = ProviderResult("wikivoyage","destinations",error="network_error")
        seed = {"name":"Coorg","issues":[]}
        result = research_candidates(self.user,self.state,[seed])
        self.assertEqual(result[0]["name"],"Coorg")
        self.assertIn("offline seed",result[0]["issues"][0])
        self.assertEqual(seed["issues"],[])

    def test_external_search_links_encode_dates_without_claiming_inventory(self):
        links = external_links(self.state,{"name":"Coorg","source":"javascript:alert(1)"})
        hotel = next(x for x in links if "booking.com" in x["url"])
        params = parse_qs(urlsplit(hotel["url"]).query)
        self.assertEqual(params["checkin"],["2026-10-02"])
        self.assertEqual(params["group_adults"],["2"])
        self.assertTrue(all(x["availability"] == "UNKNOWN" and x["verified_at"] is None for x in links))
        self.assertTrue(all(x["url"].startswith("https://") for x in links))
        self.assertNotIn(self.user.email,str(links))

    def test_booking_sites_are_plain_reviewed_https_home_pages(self):
        sites = booking_sites()
        self.assertEqual(len(sites),len(BOOKING_SITES))
        self.assertEqual({s["category"] for s in sites},{"hotels","flights","buses"})
        for site in sites:
            with self.subTest(site=site["label"]):
                parts = urlsplit(site["url"])
                self.assertEqual((parts.scheme,parts.path,parts.query,parts.fragment),("https","/","",""))
                self.assertEqual(normalized_link(site["url"]),site["url"])

    def test_unsafe_booking_site_entries_are_dropped(self):
        unsafe = [("hotels","Bad",url) for url in ("http://example.org/","javascript:alert(1)","https://user:pw@example.org/",
            "https://example.org/?ss=Coorg","https://example.org/#Coorg","https://localhost/","https://HOST.example.org/")]
        with patch("apps.mobility.services.travel.links.BOOKING_SITES",unsafe):
            self.assertEqual(booking_sites(),[])

    def test_session_payload_offers_booking_sites_with_no_trip_data(self):
        session = new_session(self.user)
        session.state = self.state
        session.save()
        self.client.force_login(self.user)
        sites = self.client.get(f"/api/mobility/planner/sessions/{session.pk}/").json()["booking_sites"]
        self.assertEqual([s["url"] for s in sites],[u for _,_,u in BOOKING_SITES])
        for private in ("Bengaluru","2026-10-02","2026-10-05","15000",self.user.email):
            self.assertNotIn(private,str(sites))

    def test_search_link_labels_name_the_trip_details_in_the_url(self):
        def by_path(state):
            links = external_links(state,{"name":"Coorg"})
            return {urlsplit(x["url"]).path:x for x in links}
        full = by_path(self.state)
        self.assertEqual(full["/searchresults.html"]["label"],"Search Booking.com with your traveller and room counts and dates")
        self.assertEqual(full["/travel/flights"]["label"],"Search Google Flights with your start city and dates")
        self.assertEqual(parse_qs(urlsplit(full["/travel/flights"]["url"]).query)["q"],["Flights from Bengaluru to Coorg 2026-10-02 2026-10-05"])
        self.assertEqual(full["/maps/dir/"]["label"],"Check route on Google Maps from your start city")
        bare = by_path({"number_of_travelers":fact(1),"origin":fact("My family private@example.org")})
        self.assertEqual(bare["/searchresults.html"]["label"],"Search Booking.com with your traveller and room counts")
        self.assertNotIn("checkin",bare["/searchresults.html"]["url"])
        self.assertEqual(bare["/travel/flights"]["label"],"Search Google Flights")
        self.assertEqual(parse_qs(urlsplit(bare["/travel/flights"]["url"]).query)["q"],["Flights to Coorg"])
        self.assertNotIn("/maps/dir/",bare)
        self.assertNotIn("private",str(bare))

    def test_overpass_status_matches_what_the_https_transport_accepts(self):
        for url, reason in (("http://overpass.example.org/api/interpreter","invalid_TRAVEL_OVERPASS_URL"),
                ("https://user:pw@overpass.example.org/api/interpreter","invalid_TRAVEL_OVERPASS_URL"),
                ("https://overpass.example.org/api/interpreter#x","invalid_TRAVEL_OVERPASS_URL"),
                ("https://localhost/api/interpreter","invalid_TRAVEL_OVERPASS_URL"),
                ("https://overpass-api.de./api/interpreter","public_overpass_backend_not_enabled_use_authorized_instance"),
                ("https://LZ4.Overpass-API.de/api/interpreter","public_overpass_backend_not_enabled_use_authorized_instance"),
                ("https://overpass.example.org/api/interpreter","")):
            with self.subTest(url=url), patch.dict("os.environ",{"TRAVEL_OVERPASS_URL":url}):
                self.assertEqual(OverpassPlaces().unavailable_reason(),reason)

    def test_withdrawing_searxng_terms_isolates_results_cached_under_them(self):
        with patch.dict("os.environ",{"TRAVEL_SEARXNG_URL":"https://search.example.org/search","TRAVEL_SEARXNG_TERMS_CONFIRMED":"true"}):
            confirmed = SearXNGSearch().cache_partition
        with patch.dict("os.environ",{"TRAVEL_SEARXNG_URL":"https://search.example.org/search","TRAVEL_SEARXNG_TERMS_CONFIRMED":"false"}):
            self.assertNotEqual(SearXNGSearch().cache_partition,confirmed)

    def test_wiki_search_is_labeled_as_community_reference(self):
        provider = WikivoyageSearch()
        p = provider.parameters({"destination":"Coorg","topic":"permits"})
        result = provider.normalize({"query":{"search":[{"title":"Coorg","snippet":"<span>Travel</span> guide"}]}},p)
        self.assertEqual(result["findings"][0]["source_type"],"community")
        self.assertEqual(result["findings"][0]["snippet"],"Travel guide")
        self.assertIn("not current authoritative",result["coverage"])
