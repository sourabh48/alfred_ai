"""Search produces evidence leads, never inferred prices, inventory or rules."""
from datetime import date, timedelta
import hashlib
import os
import re
from urllib.parse import quote, urlsplit

from django.utils.html import strip_tags

from alfred_ai.services.public_http import normalized_link
from .base import Provider, ProviderError, number, request_json


TOPICS = {
    "discovery":"destinations travel guide", "permits":"permit entry requirements official",
    "closures":"road closure traffic advisory official", "hotels":"hotels stays parking",
    "trains":"train schedule official railway", "flights":"flights airline schedule",
    "buses":"bus timetable operator", "camping":"camping permitted official",
    "attractions":"attractions opening hours official", "fuel":"fuel price official",
    "tolls":"road toll charges official", "routing":"motorcycle road restrictions official",
}
MODES = {"ride":"motorcycle", "roadtrip":"car", "train":"train", "flight":"flight", "bus":"bus", "mixed":""}


def public_place(value):
    """Only short geographic slots; never send messages, identifiers or profile blobs."""
    text = str(value or "").strip()
    if not 2 <= len(text) <= 100 or len(text.split()) > 7:
        return ""
    if not all(c.isalpha() or c in " .,'()-" for c in text):
        return ""
    if re.search(r"\b(?:email|salary|account|registration|password|my|wife|husband|family|phone|passport)\b", text, re.I):
        return ""
    return text


def source_type(url):
    host = urlsplit(url).hostname or ""
    def within(domain):
        return host == domain or host.endswith("."+domain)
    if any(within(d) for d in ("gov.in", "nic.in", "gov.uk", "gov")):
        return "official_authority", 1
    if any(within(d) for d in ("irctc.co.in", "ksrtc.in", "ksrtc.kerala.gov.in", "airindia.com", "goindigo.in")):
        return "official_operator", 2
    if any(within(d) for d in ("keralatourism.org", "karnatakatourism.org", "incredibleindia.gov.in")):
        return "official_tourism", 4
    if any(within(d) for d in ("booking.com", "agoda.com", "makemytrip.com", "skyscanner.net")):
        return "travel_platform", 5
    if any(within(d) for d in ("thehindu.com", "indianexpress.com", "reuters.com", "bbc.com")):
        return "news", 6
    if any(within(d) for d in ("wikivoyage.org", "wikipedia.org", "openstreetmap.org")):
        return "community", 7
    return "general_web", 8


class WebSearchProvider(Provider):
    category = "web"
    ttl = timedelta(hours=6)
    min_interval = 0
    allowed_parameters = {"destination", "origin", "topic", "date", "mode"}
    limits = {"minute":5, "hour":30, "day":100, "month":500}

    def parameters(self, parameters):
        p = super().parameters(parameters)
        destination = public_place(p.get("destination"))
        origin = public_place(p.get("origin"))
        topic = p.get("topic", "discovery")
        if topic not in TOPICS or not (destination or origin):
            raise ProviderError("invalid_public_search_slots")
        clean = {"destination":destination, "origin":origin, "topic":topic,
                 "mode":p.get("mode") if p.get("mode") in MODES else "mixed"}
        if p.get("date"):
            clean["date"] = date.fromisoformat(str(p["date"])).isoformat()
        return clean

    def search_query(self, p):
        location = " to ".join(filter(None, [p.get("origin"), p.get("destination")]))
        terms = [location, MODES.get(p.get("mode"), ""), TOPICS[p["topic"]]]
        return " ".join(filter(None, terms)) + (" "+p["date"][:7] if p.get("date") else "")

    def cache_ttl(self, p):
        return timedelta(minutes=30) if p["topic"] in {"hotels","flights","trains","buses"} else self.ttl

    def normalize(self, raw, p):
        rows = raw.get("web", {}).get("results", []) if self.name == "brave" else raw.get("results", [])
        if not isinstance(rows, list):
            raise ProviderError("malformed_response")
        findings, seen = [], set()
        for row in rows[:20]:
            url = normalized_link(row.get("url"))
            if not url or url in seen:
                continue
            seen.add(url)
            kind, priority = source_type(url)
            findings.append({"title":strip_tags(str(row.get("title", "")))[:200], "source_url":url,
                "snippet":strip_tags(str(row.get("description") or row.get("content") or ""))[:600],
                "source_type":kind, "source_priority":priority,
                "verification_state":"discovery_lead", "availability":"UNKNOWN",
                "rule_status":"unverified", "published_at":str(row.get("page_age") or row.get("publishedDate") or "")[:60]})
        return {"query":self.search_query(p), "findings":sorted(findings, key=lambda f:f["source_priority"])[:8],
                "verification_state":"discovery_leads_only", "coverage":"Search index results; source pages not independently fetched. No prices, rules or availability inferred."}


class BraveSearch(WebSearchProvider):
    name = "brave"
    source_url = "https://brave.com/search/api/"
    attribution = "Brave Search API; original sources linked"

    @property
    def cache_partition(self):
        # Terms opt-out also isolates data previously stored under that permission.
        return hashlib.sha256((os.getenv("TRAVEL_BRAVE_API_KEY", "")+os.getenv("TRAVEL_BRAVE_STORAGE_ALLOWED", "")).encode()).hexdigest()

    def unavailable_reason(self):
        if not os.getenv("TRAVEL_BRAVE_API_KEY"):
            return "missing_TRAVEL_BRAVE_API_KEY"
        if os.getenv("TRAVEL_BRAVE_STORAGE_ALLOWED") != "true":
            return "TRAVEL_BRAVE_STORAGE_ALLOWED_requires_plan_storage_rights"
        if os.getenv("TRAVEL_BRAVE_ALLOW_PAID_SEARCH") != "true":
            return "TRAVEL_BRAVE_ALLOW_PAID_SEARCH_required"
        return ""

    def fetch(self, p):
        return request_json("GET", "https://api.search.brave.com/res/v1/web/search",
            params={"q":self.search_query(p), "count":8, "search_lang":"en", "safesearch":"moderate"},
            headers={"X-Subscription-Token":os.environ["TRAVEL_BRAVE_API_KEY"]})


class SearXNGSearch(WebSearchProvider):
    name = "searxng"
    source_url = "https://docs.searxng.org/dev/search_api.html"
    attribution = "Configured SearXNG instance; original sources linked"

    @property
    def cache_partition(self):
        return hashlib.sha256(os.getenv("TRAVEL_SEARXNG_URL", "").encode()).hexdigest()

    def unavailable_reason(self):
        endpoint = os.getenv("TRAVEL_SEARXNG_URL", "")
        if not endpoint:
            return "missing_TRAVEL_SEARXNG_URL"
        if not normalized_link(endpoint) or urlsplit(endpoint).query or urlsplit(endpoint).fragment:
            return "invalid_TRAVEL_SEARXNG_URL"
        return "" if os.getenv("TRAVEL_SEARXNG_TERMS_CONFIRMED") == "true" else "TRAVEL_SEARXNG_TERMS_CONFIRMED_required"

    def fetch(self, p):
        return request_json("GET", os.environ["TRAVEL_SEARXNG_URL"], params={"q":self.search_query(p),"format":"json","safesearch":1})


class WikivoyageSearch(WebSearchProvider):
    name = "wikivoyage"
    source_url = "https://en.wikivoyage.org/"
    attribution = "Wikivoyage contributors, CC BY-SA 4.0; article links provide contributor history"

    def unavailable_reason(self):
        return "web_research_disabled" if os.getenv("TRAVEL_WEB_ENABLED", "true") != "true" else ""

    def fetch(self, p):
        # Travel-guide index is a limited fallback, not a general web search engine.
        text = p.get("destination") or p.get("origin")
        return request_json("GET", "https://en.wikivoyage.org/w/api.php", params={"action":"query", "format":"json",
            "formatversion":2, "list":"search", "srsearch":text, "srnamespace":0,"srlimit":8,"maxlag":5})

    def normalize(self, raw, p):
        if raw.get("error"):
            raise ProviderError("wiki_unavailable", retry_after=60)
        rows = [{"url":"https://en.wikivoyage.org/wiki/"+quote(r["title"].replace(" ","_")),
                 "title":r["title"], "content":r.get("snippet","")} for r in raw.get("query",{}).get("search",[])]
        result = super().normalize({"results":rows}, p)
        result["query"] = p.get("destination") or p.get("origin")
        result["coverage"] = "Travel-guide search only; community reference, not current authoritative access or inventory."
        return result


class WikivoyageDestinations(WikivoyageSearch):
    category = "destinations"
    version = 2
    ttl = timedelta(days=14)
    allowed_parameters = {"latitude", "longitude", "radius_km", "interest"}
    interests = {"camping", "hiking", "beach", "waterfall", "heritage", "nature"}

    def parameters(self, parameters):
        p = Provider.parameters(self, parameters)
        return {"latitude":round(number(p["latitude"],low=-90,high=90),3),
                "longitude":round(number(p["longitude"],low=-180,high=180),3),
                "radius_km":int(number(p.get("radius_km",300),low=25,high=600)),
                "interest":p.get("interest") if p.get("interest") in self.interests else ""}

    def cache_ttl(self, p):
        return self.ttl

    def fetch(self, p):
        text = f"nearcoord:{p['radius_km']}km,{p['latitude']},{p['longitude']} -incategory:\"Region articles\" -incategory:\"Country articles\""
        if p["interest"]:
            text += " "+p["interest"]
        return request_json("GET", "https://en.wikivoyage.org/w/api.php", params={"action":"query", "format":"json",
            "formatversion":2,"generator":"search","gsrsearch":text,"gsrnamespace":0,"gsrlimit":20,
            "prop":"coordinates|info", "inprop":"url", "coprimary":"primary", "colimit":50, "maxlag":5})

    def normalize(self, raw, p):
        if raw.get("error"):
            raise ProviderError("wiki_unavailable", retry_after=60)
        places, seen = [], set()
        pages = raw.get("query",{}).get("pages",[])
        if not isinstance(pages, list):
            raise ProviderError("malformed_response")
        for row in pages[:20]:
            if row.get("ns",0) != 0 or not row.get("coordinates"):
                continue
            title = str(row["title"])[:160]
            if title.casefold() in seen:
                continue
            seen.add(title.casefold())
            coords = row["coordinates"][0]
            source = "https://en.wikivoyage.org/wiki/"+quote(title.replace(" ","_"))
            places.append({"id":"wikivoyage:"+str(int(row["pageid"])),"name":title,
                "lat":number(coords["lat"],low=-90,high=90),"lon":number(coords["lon"],low=-180,high=180),
                "source":source,"authority":"Wikivoyage contributors (community)","source_type":"community",
                "styles":[],"activities":[],"stay":"Search stays near the destination; inventory unverified",
                "nightly":1500,"nightly_freshness":"ESTIMATED",
                "caution":"Community destination reference; verify access and current conditions with the authority.",
                "verification_state":"destination_reference", "popularity":"UNKNOWN"})
        return {"destinations":places, "coverage":"Geotagged English Wikivoyage travel guides; incomplete community coverage, not an official list."}
