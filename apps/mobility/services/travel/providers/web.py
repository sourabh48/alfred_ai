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
        # As with Brave, withdrawing the terms confirmation isolates what was stored under it.
        return hashlib.sha256((os.getenv("TRAVEL_SEARXNG_URL", "")+os.getenv("TRAVEL_SEARXNG_TERMS_CONFIRMED", "")).encode()).hexdigest()

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


SLEEP_SECTION = re.compile(r"^==\s*Sleep\s*==\s*$", re.M | re.I)
NEXT_SECTION = re.compile(r"^==[^=].*==\s*$", re.M)
SUBSECTION = re.compile(r"^===\s*([^=]+?)\s*===\s*$", re.M)


def _templates(text):
    """Top-level {{...}} bodies, tolerating nesting; unbalanced text is skipped."""
    found, depth, start, index = [], 0, 0, 0
    while index < len(text) - 1:
        pair = text[index:index+2]
        if pair == "{{":
            if depth == 0:
                start = index + 2
            depth += 1; index += 2; continue
        if pair == "}}" and depth:
            depth -= 1; index += 2
            if depth == 0:
                found.append((start - 2, text[start:index-2]))
            continue
        index += 1
    return found


def _fields(body):
    """Split template parameters on top-level pipes only."""
    parts, depth, current = [], 0, ""
    for index, char in enumerate(body):
        pair = body[index:index+2]
        if pair in ("{{", "[["):
            depth += 1
        elif pair in ("}}", "]]") and depth:
            depth -= 1
        if char == "|" and depth == 0:
            parts.append(current); current = ""
        else:
            current += char
    parts.append(current)
    fields = {}
    for part in parts[1:]:
        key, sep, value = part.partition("=")
        if sep:
            fields[key.strip().lower()] = value.strip()
    return parts[0].strip().lower(), fields


def _plain(value, limit):
    value = re.sub(r"<!--.*?-->", "", value or "", flags=re.S)
    for _ in range(3):  # nested markup
        value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", value)
    value = re.sub(r"\[https?://\S+\]", "", value)
    value = strip_tags(value).replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _insecure_host(url):
    url = (url or "").strip()
    if not url.lower().startswith("http://") or normalized_link("https://" + url[7:]) == "":
        return ""
    return urlsplit(normalized_link("https://" + url[7:])).hostname or ""


def sleep_listings(wikitext, limit=30):
    """Wikivoyage Sleep-section listings as unverified guide leads; free-text prices are never parsed as money."""
    heading = SLEEP_SECTION.search(wikitext or "")
    if not heading:
        return []
    following = NEXT_SECTION.search(wikitext, heading.end())
    section = wikitext[heading.end():following.start() if following else len(wikitext)]
    tiers = [(m.start(), _plain(m.group(1), 40)) for m in SUBSECTION.finditer(section)]
    listings = []
    for position, body in _templates(section):
        name, fields = _fields(body)
        if name not in ("sleep", "listing") or (name == "listing" and fields.get("type", "").lower() != "sleep"):
            continue
        title = _plain(fields.get("name"), 200)
        if not title:
            continue
        try:
            lat, lon = number(fields.get("lat"), low=-90, high=90), number(fields.get("long"), low=-180, high=180)
        except (ProviderError, TypeError, ValueError):
            lat = lon = None
        phone = re.sub(r"[^0-9+() -]", "", fields.get("phone", ""))[:40].strip()
        listings.append({"name": title, "category": "hotel",
            "tier": next((tier for start, tier in reversed(tiers) if start < position), ""),
            "price_text": _plain(fields.get("price"), 120), "website": normalized_link(fields.get("url", "")),
            # http-only sites are shown as plain text, never as a link ALFRED vouches for.
            "website_host": _insecure_host(fields.get("url", "")),
            "phone": phone, "address": _plain(fields.get("address"), 200),
            "check_in": _plain(fields.get("checkin"), 40), "check_out": _plain(fields.get("checkout"), 40),
            "description": _plain(fields.get("content"), 400), "listing_updated": _plain(fields.get("lastedit"), 20),
            "lat": lat, "lon": lon, "availability": "UNKNOWN"})
        if len(listings) >= limit:
            break
    return listings


class WikivoyageStays(WikivoyageSearch):
    """Accommodation listings from the destination's Wikivoyage article, via the official MediaWiki API."""
    category = "stays_guide"
    ttl = timedelta(days=14)
    allowed_parameters = {"destination"}

    def parameters(self, parameters):
        p = Provider.parameters(self, parameters)
        title = re.sub(r"\s+", " ", str(p.get("destination") or "")).strip()[:120]
        if not title or any(c in title for c in "[]{}|#<>"):
            raise ProviderError("destination_required")
        return {"destination": title}

    def cache_ttl(self, p):
        return self.ttl

    def fetch(self, p):
        # Only the public place name is sent; budgets, dates and history never leave.
        return request_json("GET", "https://en.wikivoyage.org/w/api.php", params={"action":"query", "format":"json",
            "formatversion":2, "prop":"revisions", "rvprop":"content|timestamp", "rvslots":"main",
            "titles":p["destination"], "redirects":1, "maxlag":5})

    def normalize(self, raw, p):
        if raw.get("error"):
            raise ProviderError("wiki_unavailable", retry_after=60)
        pages = raw.get("query", {}).get("pages", [])
        if not isinstance(pages, list):
            raise ProviderError("malformed_response")
        page = next((row for row in pages if not row.get("missing") and row.get("revisions")), None)
        if not page:
            return {"options": [], "coverage": "No Wikivoyage article matched this destination name."}
        revision = page["revisions"][0]
        text = revision.get("slots", {}).get("main", {}).get("content", "")
        title = str(page.get("title", p["destination"]))[:160]
        article = "https://en.wikivoyage.org/wiki/" + quote(title.replace(" ", "_"))
        options = [{**item, "id": f"wikivoyage-stay:{int(page['pageid'])}:{index}", "provider": "Wikivoyage",
                    "source_url": article + "#Sleep"} for index, item in enumerate(sleep_listings(text))]
        return {"options": options, "article": title, "article_updated": str(revision.get("timestamp", ""))[:20],
                "coverage": "Community travel-guide listings, CC BY-SA 4.0. Prices are as written by contributors, "
                            "not current rates; availability, parking and condition are unverified."}


LODGING_TYPES = {"Hotel", "Motel", "Hostel", "Resort", "BedAndBreakfast", "LodgingBusiness", "Campground",
                 "VacationRental", "SkiResort", "GuestHouse"}
ROBOTS_AGENT = "ALFRED-travel"


def _ld_items(node):
    if isinstance(node, list):
        for item in node:
            yield from _ld_items(item)
    elif isinstance(node, dict):
        yield node
        yield from _ld_items(node.get("@graph", []))


def _text(value, limit=200):
    if isinstance(value, dict):
        value = value.get("name") or value.get("@value") or ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return ""
    return re.sub(r"\s+", " ", strip_tags(str(value))).strip()[:limit]


def lodging_details(html):
    """schema.org lodging facts the property publishes about itself; never prices or availability."""
    from bs4 import BeautifulSoup
    import json
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"})[:20]:
        try:
            data = json.loads(script.string or script.get_text() or "")
        except ValueError:
            continue
        for item in _ld_items(data):
            kinds = item.get("@type")
            if not LODGING_TYPES & set(kinds if isinstance(kinds, list) else [kinds]) - {None}:
                continue
            address = item.get("address")
            if isinstance(address, dict):
                address = ", ".join(filter(None, (_text(address.get(k), 120) for k in
                    ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"))))
            star = item.get("starRating")
            rating = item.get("aggregateRating") if isinstance(item.get("aggregateRating"), dict) else {}
            amenities = item.get("amenityFeature") or []
            geo = item.get("geo") if isinstance(item.get("geo"), dict) else {}
            def coordinate(key, bound):
                try:
                    return number(geo.get(key), low=-bound, high=bound)
                except (ValueError, TypeError):
                    return None
            details = {
                "name": _text(item.get("name"), 160), "description": _text(item.get("description"), 400),
                "address": _text(address, 300), "phone": re.sub(r"[^0-9+() -]", "", _text(item.get("telephone"), 40)),
                "check_in": _text(item.get("checkinTime"), 40), "check_out": _text(item.get("checkoutTime"), 40),
                "price_range": _text(item.get("priceRange"), 80),
                "star_rating": _text(star.get("ratingValue") if isinstance(star, dict) else star, 10),
                "rating": _text(rating.get("ratingValue"), 10), "review_count": _text(rating.get("reviewCount") or rating.get("ratingCount"), 12),
                "pets_allowed": _text(item.get("petsAllowed"), 60) if not isinstance(item.get("petsAllowed"), bool) else ("Yes" if item["petsAllowed"] else "No"),
                "amenities": [name for name in (_text(a, 60) for a in (amenities if isinstance(amenities, list) else [amenities])[:40]
                              if not (isinstance(a, dict) and a.get("value") is False)) if name][:20],
                "lat": coordinate("latitude", 90), "lon": coordinate("longitude", 180),
            }
            return {key: value for key, value in details.items() if value not in ("", [], None)}
    # No structured data: keep only the page's own one-line summary, clearly labelled as such.
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    summary = _text(meta.get("content") if meta else "", 400)
    return {"page_summary": summary} if summary else {}


def robots_allows(url, fetch_text):
    """RFC 9309: a missing robots.txt allows; anything unreadable is treated as a refusal."""
    from alfred_ai.services.public_http import robots_allows as allows
    return allows(url, fetch_text, ROBOTS_AGENT)


class HotelWebsite(Provider):
    """One property's own public page, opened on the owner's request for a guide-listed website."""
    name = "hotel_website"
    category = "stay_website"
    attribution = "Details published by the property on its own website; not verified by ALFRED"
    ttl = timedelta(days=7)
    limits = {"minute": 5, "hour": 30, "day": 100, "month": 1000}
    min_interval = 2
    allowed_parameters = {"url"}

    def __init__(self, url=""):
        self.source_url = normalized_link(url).split("#", 1)[0]

    def unavailable_reason(self):
        return "web_research_disabled" if os.getenv("TRAVEL_WEB_ENABLED", "true") != "true" else ""

    def parameters(self, parameters):
        url = normalized_link(Provider.parameters(self, parameters).get("url")).split("#", 1)[0]
        if not url or url != self.source_url:
            raise ProviderError("invalid_parameters")
        return {"url": url}

    @staticmethod
    def _get(url, content_types, statuses=(200,)):
        from alfred_ai.services.public_http import PublicHTTPError
        from . import base  # The shared boundary that tests and other providers patch.
        try:
            response = base.request("GET", url, content_types=content_types, accepted_statuses=statuses, max_bytes=2_000_000)
        except PublicHTTPError as exc:
            raise ProviderError(exc.code, retry_after=exc.retry_after) from None
        return response

    def fetch(self, p):
        def robots(url):
            try:
                response = self._get(url, ("text/plain", "text/html"), (200, 404, 410))
            except ProviderError:
                raise ProviderError("robots_unreadable", retry_after=3600) from None
            # An HTML page in place of robots.txt has no rules, like a missing file.
            return response.status, response.content.decode("utf-8", "replace") if response.content_type == "text/plain" else ""
        if not robots_allows(p["url"], robots):
            raise ProviderError("robots_disallowed", retry_after=86400)
        response = self._get(p["url"], ("text/html", "application/xhtml+xml"))
        return response.content.decode("utf-8", "replace"), response.response_hash

    def normalize(self, raw, p):
        details = lodging_details(raw)
        return {"website": p["url"], "website_host": urlsplit(p["url"]).hostname, "details": details,
                "coverage": ("Read from the property's own website (schema.org data). These are the property's own statements; "
                             "prices and availability are not current rates." if set(details) - {"page_summary"} else
                             "This website has no structured hotel details; shown is its own page summary. Open it to read more." if details else
                             "This website does not publish machine-readable hotel details. Open it to read them yourself.")}
