"""Public web results for a general Ask ALFRED question: when the owner ticks "Look this up online", or when ALFRED decides
a plainly public question needs current or reference information that saved memories do not hold.

Only the question text leaves this PC. Automatic lookup sends general and current public questions that saved data does not
answer; a question that may be about someone's private life (a name, a relation, a health, legal or money-trouble word)
waits until the owner confirms the exact text, and one about the owner or with amounts, numbers, emails or keys never leaves.
No records, memories or history are ever sent. ALFRED does not cache the question or the results, but Wikipedia and
Google receive the text and may keep it under their own policies.
"""
import html
import re
from urllib.parse import quote_plus, urlsplit

import feedparser

from alfred_ai.services import public_http

from .prompt_injection import finding

USER_AGENT = "ALFRED-local/2.0 (+https://github.com/sourabh48/alfred_ai)"  # Wikimedia refuses agents without a contact link
# Amounts (digits or spelled out), long digit runs (account, card, phone and ID numbers), emails, keys and file paths stay on this PC.
_NUMBER = ("one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen"
           "|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|half|couple")
_SCALE = "thousand|lakhs?|lacs?|crores?|million|billion"
PRIVATE_IN_QUESTION = re.compile(
    r"(?i)sk-[a-z0-9_-]{8,}|AKIA[A-Z0-9]{12,}|\b[a-z]:[\\/]|/(?:home|users|tmp)/|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|(?:\d[ -]?){6,}|[$€£₹]\s*\d|\b(?:rs|inr|usd|eur|gbp)\.?\s*\d|\d[\d,.]*\s*(?:k|thousand|lakhs?|lacs?|crores?|cr|lpa|million|rupees?|inr|rs|/-)\b"
    rf"|\b(?:{_NUMBER})(?:[\s-]+(?:and|a|{_NUMBER}|{_SCALE}))*[\s-]+(?:{_SCALE}|rupees?|dollars?|euros?|pounds?|bucks|lpa)\b"
    r"|\b(?:password|passcode|otp|pin|cvv|secret|token|bearer|aadhaar|aadhar|pan number|ifsc)\b")
TAG = re.compile(r"<[^>]+>")


PRIVATE_MESSAGE = ("This question has details that look private (an amount, number, email or key), so ALFRED "
                   "did not search online. Ask it without those details.")


class PrivateQuestion(PermissionError):
    pass


# Questions about the person or about ALFRED itself are answered from memory, never searched.
PERSONAL = re.compile(r"(?i)\b(?:my|me|mine|myself|i|i'm|i've|i'd|our|ours|we|you|your|alfred)\b")
# Words that mean the answer changes over time, so saved memories cannot hold it.
CURRENT = re.compile(r"(?i)\b(?:latest|today|tonight|tomorrow|yesterday|now|current(?:ly)?|recent(?:ly)?|news|this (?:week|month|year)"
                     r"|20\d\d|prices?|rates?|scores?|weather|forecast|who won|elections?|released?|launch(?:ed|es)?|happening|update[sd]?)\b")
GENERAL = re.compile(r"(?i)^\s*(?:who|what|when|where|which|why|how|is|are|was|were|does|did|tell me about|explain|define|meaning of)\b")

# With no reliable way to identify people in free text, automatic searches use complete public query patterns.
PUBLIC_LOOKUP = re.compile(
    r"(?i)(?:"
    r"(?:what (?:is|are) (?:an? )?|define |explain |meaning of )"
    r"(?:mutual funds?|index funds?|systematic investment plans?|exchange.traded funds?|compound interest|inflation|repo rate)"
    r"|how does (?:a sip|compound interest|an index fund) work"
    r"|what is the capital of (?:india|france|japan|germany|canada|australia|the united states)"
    r"|(?:what is the )?(?:current |latest )?repo rate(?: in india| news)?"
    r"|latest mutual fund news|who won the election today"
    r"|interest rates in (?:india|the us|the uk)(?: this year| today)?"
    r"|(?:petrol price|weather|weather forecast) in (?:bengaluru|bangalore|kolkata|mumbai|delhi|chennai|hyderabad|pune|mysuru)"
    r"(?: today| tomorrow)?"
    r")\??"
)


# Owner 2026-11-19: research by itself when saved data has nothing. Owner 2026-11-20: online data is used without asking,
# so a name alone no longer waits; a family or work relation, or a health, legal or money-trouble word still waits for a tap.
PRIVATE_LIFE = re.compile(
    r"(?i)\b(?:friend|wife|husband|partner|son|daughter|mother|father|mom|dad|brother|sister|cousin|uncle|aunt|colleague|boss"
    r"|neighbou?r|girlfriend|boyfriend|ex|diagnos\w*|hiv|aids|cancer|pregnan\w*|depression|anxiety|therapy|treatment|disease"
    r"|illness|sick|arrest\w*|jail|court|lawsuit|divorce|affair|bankrupt\w*|debt|fired|laid off|rent|salary|avoid\w*)\b")


def clearly_public(question):
    """A complete recognized public query, or a general one with no sign of anyone's private life."""
    if PUBLIC_LOOKUP.fullmatch(question):
        return True
    return (not PERSONAL.search(question) and not PRIVATE_LIFE.search(question)
            and bool(GENERAL.search(question) or CURRENT.search(question)))


def should_search(question, memories=()):
    """Look online by itself only for a plainly public question that saved memories do not answer."""
    try:
        question = check_public(question)
    except PrivateQuestion:
        return False
    return clearly_public(question) and (bool(CURRENT.search(question)) or not memories)


def offer(question, memories=()):
    """The exact text a lookup would send, when looking online could help but the question may be about someone's private life."""
    try:
        question = check_public(question)
    except PrivateQuestion:
        return None
    wanted = CURRENT.search(question) or (not memories and GENERAL.search(question))
    return question if wanted and not PERSONAL.search(question) and not clearly_public(question) else None


def check_public(question):
    if not isinstance(question, str) or not question.strip() or len(question) > 300 or PRIVATE_IN_QUESTION.search(question):
        raise PrivateQuestion(PRIVATE_MESSAGE)
    return " ".join(question.split())


def _clean(text, limit):
    return html.unescape(TAG.sub("", text or "")).strip()[:limit]


def _wikipedia(question, deadline):
    response = public_http.request("GET", "https://en.wikipedia.org/w/rest.php/v1/search/page",
        params={"q": question, "limit": 3}, headers={"User-Agent": USER_AGENT}, max_bytes=300_000, deadline=deadline)
    return [{"title": _clean(page.get("title"), 200), "snippet": _clean(page.get("excerpt"), 400) or _clean(page.get("description"), 400),
             "url": "https://en.wikipedia.org/wiki/" + quote_plus(str(page.get("key", "")).replace(" ", "_"), safe="_()"),
             "source": "Wikipedia", "published": ""}
            for page in response.json().get("pages", [])[:3] if page.get("key")]


def _news(question, deadline):
    response = public_http.request("GET", f"https://news.google.com/rss/search?q={quote_plus(question)}&hl=en-IN&gl=IN&ceid=IN:en",
        headers={"User-Agent": USER_AGENT}, content_types=("application/rss+xml", "application/xml", "text/xml"),
        max_bytes=2_000_000, deadline=deadline)
    return [{"title": _clean(entry.get("title"), 300), "snippet": _clean(entry.get("summary"), 400), "url": entry.get("link", ""),
             "source": _clean((entry.get("source") or {}).get("title"), 100) or "Google News", "published": entry.get("published", "")}
            for entry in feedparser.parse(response.content).entries[:5]]


def search(question, *, deadline=None):
    """Up to eight public results as answer sources. A source that fails is skipped; the rest still count."""
    question = check_public(question)
    results = []
    for fetch in (_wikipedia, _news):
        try:
            results.extend(fetch(question, deadline))
        except (public_http.PublicHTTPError, ValueError, KeyError, TypeError, AttributeError, OSError):
            continue
    sources = []
    for item in results:
        if urlsplit(item["url"]).scheme == "https" and item["title"] and not finding(item["title"], item["snippet"]):
            sources.append({"ref": f"web-{len(sources) + 1}", "classification": "public_web_result", "url": item["url"], "data": item})
    return sources
