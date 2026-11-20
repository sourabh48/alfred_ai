"""A Gemini practice set for the local travel reader (owner choice 2026-11-20).

Gemini writes made-up Indian trip messages with the fields each one means, using the owner's own saved key. Nothing
private is sent: each request holds only the fixed instruction below, today's date and a theme. An example is kept only
when every field Gemini filled survives the reader's own clean() checks, so the local model never learns a value the
message does not support. Every tenth kept example is held back to score the fine-tuned model, never to train it.
"""
import json
import logging
import re
import time

from django.conf import settings
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError, request
from .brain import examples, remember

logger = logging.getLogger(__name__)
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
PER_CALL = 12  # 25 took about 4.9 s and often passed the web client's 5 s read limit; 12 took about 3.5 s (2026-11-20)
# Training prompts carry no "this weekend" dates, so a message using such words would teach the model to ignore them.
RELATIVE = re.compile(r"\b(?:today|tonight|tomorrow|tmrw|day after|(?:this|next|coming)\s+(?:week|weekend|month|mon|tue|wed|"
                      r"thu|fri|sat|sun)\w*)\b", re.I)
THEMES = ("a motorcycle ride with friends", "a family holiday with parents and kids", "a honeymoon or couple trip",
          "a cheap backpacking trip by train or bus", "a weekend getaway from a big city", "a trek or camping trip",
          "a beach trip", "a hill station escape", "a pilgrimage or temple visit", "a road trip by car",
          "a solo trip", "an office team outing", "a wildlife or nature trip", "a food and culture trip",
          "a short message that changes only one thing, like the place, the budget or the number of people")
INSTRUCTION = (
    "Write made-up messages that people in India send to a trip-planning assistant, and for each one the fields it states. "
    "Write the messages the way people really type in chat apps: short, casual Indian English or Hinglish, abbreviations "
    "(frnds, ppl, 2 ppl, k for thousand), small typos, no greetings. Vary them: many state only one to three details. Use real "
    "Indian places and say each place exactly as the field gives it. Never use names, phone numbers or any personal data. "
    "Today is {today}. Dates must be exact days written in the message (24-27 dec, 3rd to 5th jan, 14 feb), between {first} "
    "and {last}, never relative words like this weekend, tomorrow or next month; a trip lasts at most 15 days. Fields: "
    "destination and origin (place names as written), start_date and end_date (YYYY-MM-DD; use the next such date after today), "
    "days (whole number; equals the dates' length when dates are given), budget_rupees (whole rupees: 15k = 15000, 1 lakh = "
    "100000), budget_scope (per_person or whole_trip, only with a budget), travellers (everyone, including the writer: 'me n 3 "
    "frnds' is 4, 'me and wife' is 2), transport (ride for bikes or motorcycles, roadtrip for a car, train, bus or flight; only "
    "when the message names one), trip_styles and avoid (lists using these words when the message says them: mountain, hills, "
    "beach, forest, nature, waterfall, wildlife, history, architecture, trek, camping, photography, food, culture, nightlife, "
    "quiet, peaceful, offbeat, adventure, relaxed, scenic), food (vegetarian, vegan, halal or gluten-free) and stay (homestay, "
    "resort, hostel, hotel or camping). Leave out every field the message does not state. Reply with only a JSON array of "
    "objects like {{\"message\": \"...\", \"meant\": {{\"destination\": \"Goa\", \"travellers\": 4}}}}.")


def ask_gemini(key, theme, count, today, *, deadline):
    """One batch of made-up examples from Gemini; only the fixed instruction, today's date and the theme are sent."""
    first, last = today.fromordinal(today.toordinal() + 3), today.fromordinal(today.toordinal() + 300)
    body = {"systemInstruction": {"parts": [{"text": INSTRUCTION.format(today=today.isoformat(), first=first, last=last)}]},
            "contents": [{"role": "user", "parts": [{"text": f"Write {count} examples. Theme: {theme}."}]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 12000, "candidateCount": 1,
                                 "temperature": 1.0}}
    result = request("POST", GEMINI.format(settings.ALFRED_GEMINI_MODEL), headers={"x-goog-api-key": key}, json_body=body,
                     max_bytes=262144, deadline=deadline).json()
    candidate = (result.get("candidates") or [{}])[0]
    if candidate.get("finishReason") != "STOP":
        raise ValueError("Gemini did not finish the batch.")
    text = "".join(part.get("text", "") for part in (candidate.get("content") or {}).get("parts", [])
                   if isinstance(part, dict) and not part.get("thought"))
    items = json.loads(text)
    return items if isinstance(items, list) else []


def usable(item):
    """The example, trimmed to the reader's fields, when the reader's own checks accept every field it fills; else None."""
    from apps.mobility.services.travel.understanding import FIELDS, SCHEMA, clean
    message, meant = (item.get("message"), item.get("meant")) if isinstance(item, dict) else (None, None)
    if (not isinstance(message, str) or not 0 < len(message.strip()) <= 400 or not isinstance(meant, dict)
            or RELATIVE.search(message)):
        return None
    meant = {field: value for field, value in meant.items() if field in SCHEMA["properties"] and value not in (None, "", [])}
    kept = clean(meant, message)
    if not meant or {field for field in meant} - {FIELDS[key] for key in kept}:
        return None
    for field in ("trip_styles", "avoid"):  # every word in the list must be one the reader understands
        if any(not clean({field: [word]}, message) for word in meant.get(field, [])):
            return None
    if "available_start_date" in kept and meant.get("days", kept["trip_duration"]) != kept["trip_duration"]:
        return None
    return {"message": " ".join(message.split()), "meant": meant}


def generate(user, count=500, *, key, ask=ask_gemini, seconds=90):
    """Ask Gemini for practice examples until `count` new ones are kept; stops early when Gemini refuses or runs out of quota."""
    today, seen = timezone.localdate(), {item.get("message", "").casefold() for item in examples(user, "travel_practice")}
    kept = asked = rejected = 0
    for call in range(max(1, count // 5)):  # shortcut: at most a fifth of the target in calls, to bound free-tier use
        if kept >= count:
            break
        try:
            batch = ask(key, THEMES[call % len(THEMES)], min(PER_CALL, count - kept + 5), today,
                        deadline=time.monotonic() + seconds)
        except PublicHTTPError as exc:
            if exc.code not in ("quota_exhausted", "authorization_failed"):
                continue  # a busy or slow moment at Google; the next call may work
            logger.info("Practice set stopped: %s", exc.code)
            return {"kept": kept, "asked": asked, "rejected": rejected, "stopped": exc.code}
        except (ValueError, KeyError, TypeError, AttributeError):
            continue  # one malformed batch; the next theme may do better
        for item in batch:
            asked += 1
            example = usable(item)
            if example is None or example["message"].casefold() in seen or kept >= count:
                rejected += example is None
                continue
            seen.add(example["message"].casefold())
            remember(user, "travel_practice", {**example, "source": "gemini_practice", "held_back": kept % 10 == 9})
            kept += 1
    return {"kept": kept, "asked": asked, "rejected": rejected, "stopped": None}
