"""Public web results for a general Ask ALFRED question: when the owner ticks "Look this up online", or when ALFRED decides
the question needs current or public information that saved memories do not hold.

Only the question text leaves this PC, and only when it carries nothing that looks private. No records,
memories or history are ever sent, and results are not cached, so the question is not kept anywhere.
"""
import html
import re
from urllib.parse import quote_plus, urlsplit

import feedparser

from alfred_ai.services import public_http

USER_AGENT = "ALFRED-local/2.0 (+https://github.com/sourabh48/alfred_ai)"  # Wikimedia refuses agents without a contact link
# Amounts, long digit runs (account, card, phone and ID numbers), emails, keys and file paths stay on this PC.
PRIVATE_IN_QUESTION = re.compile(
    r"(?i)sk-[a-z0-9_-]{8,}|AKIA[A-Z0-9]{12,}|\b[a-z]:[\\/]|/(?:home|users|tmp)/|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|(?:\d[ -]?){6,}|[$€£₹]\s*\d|\b(?:rs|inr|usd|eur|gbp)\.?\s*\d|\d[\d,.]*\s*(?:k|thousand|lakhs?|lacs?|crores?|cr|lpa|million|rupees?|inr|rs|/-)\b"
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
GENERAL = re.compile(r"(?i)^\s*(?:who|what|when|where|which|why|how|is|are|was|were|does|did|tell me about|explain)\b")


def should_search(question, memories=()):
    """Look online for current or general-knowledge questions that saved memories do not answer; private-looking ones never."""
    try:
        check_public(question)
    except PrivateQuestion:
        return False
    if PERSONAL.search(question):
        return False
    return bool(CURRENT.search(question)) or (not memories and bool(GENERAL.search(question)))


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
        if urlsplit(item["url"]).scheme == "https" and item["title"]:
            sources.append({"ref": f"web-{len(sources) + 1}", "classification": "public_web_result", "url": item["url"], "data": item})
    return sources
