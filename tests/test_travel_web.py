from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.mobility.services.travel.providers.base import ProviderResult
from apps.mobility.services.travel.providers.web import BraveSearch, WikivoyageDestinations, WikivoyageSearch, source_type
from apps.mobility.services.travel.research import research_candidates, quality_contract
from apps.mobility.services.travel.links import external_links
from apps.mobility.services.travel.discovery import remember
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

    def test_wiki_search_is_labeled_as_community_reference(self):
        provider = WikivoyageSearch()
        p = provider.parameters({"destination":"Coorg","topic":"permits"})
        result = provider.normalize({"query":{"search":[{"title":"Coorg","snippet":"<span>Travel</span> guide"}]}},p)
        self.assertEqual(result["findings"][0]["source_type"],"community")
        self.assertEqual(result["findings"][0]["snippet"],"Travel guide")
        self.assertIn("not current authoritative",result["coverage"])
