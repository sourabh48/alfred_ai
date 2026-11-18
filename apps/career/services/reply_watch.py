"""Reply watch (career-ops fe9cb888, MIT, modes/reply-watch.md; owner approval 2026-11-18 to read the mailbox).

ALFRED reads the owner's own inbox read-only over IMAP with the mail login Career already uses for sending (an app
password), sorts recent employer replies into Interview, Offer, Rejected, Assessment, Need action, Auto-confirmation or
Responded, and matches them to saved opportunities. Nothing is marked read, moved, stored or sent, and no mail reaches
any model: the sorting is plain rules. A suggested stage change applies only when the owner presses Apply, through the
same stage endpoint the tracker uses.
"""
from __future__ import annotations

import email
import imaplib
import re
from datetime import timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime

from django.conf import settings
from django.utils import timezone

from .application_tracker import CLOSED_STAGES, STAGES, _clean

IMAP_HOSTS = {"smtp.gmail.com": "imap.gmail.com", "smtp.office365.com": "outlook.office365.com",
              "smtp-mail.outlook.com": "outlook.office365.com", "smtp.mail.yahoo.com": "imap.mail.yahoo.com",
              "smtp.zoho.com": "imap.zoho.com", "smtp.zoho.in": "imap.zoho.in"}
DAYS, MAX_MESSAGES, BODY_BYTES = 30, 200, 20_000
# First match wins; each rule quotes the phrase that triggered it.
RULES = (
    ("Offer", "offer", re.compile(r"\b(offer letter|pleased to (?:offer|extend)|extend(?:ing)? (?:you )?an offer|job offer)\b", re.I)),
    ("Rejected", "rejected", re.compile(r"\b(regret to inform|not (?:be )?moving forward|decided (?:to )?(?:proceed|move forward|go ahead) "
                                        r"with other|position has been filled|not been selected|unable to offer you)\b", re.I)),
    ("Interview", "interview", re.compile(r"\b(interview|schedule a (?:call|chat)|your availability|calendly\.com|meet the team)\b", re.I)),
    ("Assessment", "assessment", re.compile(r"\b(assessment|coding (?:test|challenge)|take[- ]home|hackerrank|codility|online test)\b", re.I)),
    ("Auto-confirmation", "applied", re.compile(r"\b(thank you for (?:applying|your application)|(?:we have |we've )?received your "
                                                r"application|application (?:has been )?received)\b", re.I)),
    ("Need action", None, re.compile(r"\b(please (?:send|share|complete|provide|confirm)|action required)\b", re.I)),
)
ORDER = {stage: i for i, stage in enumerate(("evaluated", "applied", "responded", "assessment", "interview", "offer"))}
NOISE = re.compile(r"\b(newsletter|unsubscribe|job alert|jobs you may like|recommended jobs|webinar)\b", re.I)
SUFFIX = re.compile(r"\b(inc|llc|ltd|limited|pvt|private|corp|corporation|co|company|technologies|technology|labs|software|"
                    r"solutions|india|group|holdings|plc|gmbh)\b\.?", re.I)


def imap_host() -> str:
    return getattr(settings, "ALFRED_IMAP_HOST", "") or IMAP_HOSTS.get((settings.ALFRED_SMTP_HOST or "").lower(), "")


def configured() -> bool:
    return bool(imap_host() and settings.ALFRED_SMTP_USER and settings.ALFRED_SMTP_PASSWORD)


def _text(value) -> str:
    try:
        return " ".join(str(make_header(decode_header(value or ""))).split())
    except (UnicodeError, LookupError, ValueError):
        return " ".join(str(value or "").split())


def _body(message) -> str:
    for part in message.walk() if message.is_multipart() else [message]:
        if part.get_content_type() == "text/plain":
            raw = part.get_payload(decode=True) or b""
            return " ".join(raw.decode(part.get_content_charset() or "utf-8", "replace").split())[:4000]
    return ""


def read_inbox(*, days: int = DAYS) -> list:
    """Recent inbox messages (sender, subject, date, a plain-text excerpt), fetched with PEEK so nothing is marked read."""
    since = (timezone.localdate() - timedelta(days=days)).strftime("%d-%b-%Y")
    box = imaplib.IMAP4_SSL(imap_host(), 993, timeout=30)
    try:
        box.login(settings.ALFRED_SMTP_USER, settings.ALFRED_SMTP_PASSWORD)
        box.select("INBOX", readonly=True)
        status, found = box.search(None, "SINCE", since)
        ids = (found[0] or b"").split()[-MAX_MESSAGES:] if status == "OK" else []
        messages = []
        for number in reversed(ids):
            status, parts = box.fetch(number, f"(BODY.PEEK[]<0.{BODY_BYTES}>)")
            raw = next((p[1] for p in parts or [] if isinstance(p, tuple)), None) if status == "OK" else None
            if raw:
                message = email.message_from_bytes(raw)
                try:
                    on = parsedate_to_datetime(message.get("Date")).date().isoformat()
                except (TypeError, ValueError, IndexError):
                    on = ""
                name, address = parseaddr(_text(message.get("From")))
                messages.append({"from_name": name[:120], "from": address[:200], "subject": _text(message.get("Subject"))[:300],
                                 "on": on, "body": _body(message)})
        return messages
    finally:
        try:
            box.logout()
        except (imaplib.IMAP4.error, OSError):
            pass


def _company_words(company: str) -> list:
    return [w for w in re.sub(r"[^a-z0-9 ]", " ", SUFFIX.sub(" ", company.casefold())).split() if len(w) >= 3]


def _match(message: dict, analyses: list):
    domain = message["from"].rsplit("@", 1)[-1].casefold()
    where = f"{message['from_name']} {message['subject']}".casefold()
    for analysis in analyses:
        words = _company_words(analysis.company or "")
        if words and (all(w in where for w in words) or "".join(words) in domain.replace("-", "")):
            return analysis
    return None


def sort_replies(messages: list, analyses: list) -> list:
    """Each matched reply with its category, the phrase that decided it and the stage change it suggests (if any)."""
    open_ones = [a for a in analyses if isinstance(a.extracted_payload, dict) and a.company]
    found = []
    for message in messages:
        analysis = _match(message, open_ones)
        if analysis is None or NOISE.search(f"{message['subject']} {message['body'][:600]}"):
            continue  # recruiting noise and mail about no saved opportunity are left alone
        text = f"{message['subject']} {message['body']}"
        category, stage, quote = "Responded", "responded", ""
        for label, rule_stage, rule in RULES:
            hit = rule.search(text)
            if hit:
                category, stage, quote = label, rule_stage, hit.group(0)
                break
        current = _clean(analysis.extracted_payload.get("application"))["stage"]
        if stage and (current in CLOSED_STAGES or stage == current or
                      (stage not in CLOSED_STAGES and ORDER.get(stage, 0) <= ORDER.get(current, -1))):
            stage = None  # never a step backwards, a repeat, or a change to a closed opportunity
        found.append({"opportunity_id": analysis.pk, "company": analysis.company, "role": analysis.job_title or "",
                      "current_stage": current or "not set", "category": category, "because": quote,
                      "suggested_stage": stage if stage in STAGES else None, "on": message["on"],
                      "from": message["from"], "subject": message["subject"]})
    return found


def check(user) -> dict:
    from apps.career.models import CareerJobAnalysis

    if not configured():
        raise ValueError("Set up Career email first (Settings, your mail app password); reply watch reads the same mailbox.")
    analyses = list(CareerJobAnalysis.objects.filter(user=user).order_by("-updated_at", "-id")[:300])
    replies = sort_replies(read_inbox(), analyses)
    return {"replies": replies, "checked_days": DAYS, "mailbox": settings.ALFRED_SMTP_USER,
            "basis": f"Read just now from your inbox (last {DAYS} days), read-only: nothing was marked read, moved or kept. "
                     "Sorted by plain rules; no AI read your mail. A change applies only when you press Apply."}
