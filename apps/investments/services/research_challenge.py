"""INVEST2-001 independent challenge: the local model argues against the evidence packet, point by point.

TradingAgents (Apache-2.0, pin e8f5503e) has bull and bear researchers debate before a decision. Here the debate is one
bounded round on the local Ollama model only: it sees the packet's dated points, never the owner's records, and may only
question them. It cannot add figures: any objection that states a number is dropped, because only the packet's dated
values count. Output is labelled as hypotheses; nothing is stored or changed.
"""
from __future__ import annotations

import json
import re
import time

from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable

SECONDS = 120  # measured 2026-11-07: the CPU-only local model writes about 3 tokens a second here
TEXT = 300
DIGIT = re.compile(r"\d")
JSON_OBJECT = re.compile(r"\{.*\}", re.S)


def challenge_payload(packet: dict) -> dict:
    points = {f"F{i}": p for i, p in enumerate(packet["bullish"], 1)} | {f"A{i}": p for i, p in enumerate(packet["bearish"], 1)}
    lean = "for" if len(packet["bullish"]) > len(packet["bearish"]) else "against" if packet["bearish"] else "neither way"
    return {
        "task": ("Act as an independent sceptic of this stock evidence packet. The packet leans " + lean + ". "
                 "For up to three points, say in under twenty-five words why the point could mislead (one-off items, accounting, "
                 "cycle, sector norms, stale data). Then name up to two risks the packet does not cover. Do not state any number, "
                 "price, rating or recommendation. Reply only with JSON: "
                 '{"objections":[{"point":"F1","why":"..."}],"overlooked":["..."]}'),
        "symbol": packet["symbol"],
        "points": {key: {"point": p["point"], "as_of": p["as_of"]} for key, p in points.items()},
        "valuation": packet["valuation"].get("reason") or packet["valuation"].get("basis"),
        "already_missing": packet["missing_evidence"],
    }, points


def _clean(value):
    text = " ".join(str(value or "").split())[:TEXT]
    return text if text and not DIGIT.search(text) else None


def parse_challenge(raw: str, points: dict) -> dict:
    """Keep only well-formed objections to real points, without numbers; anything else is reported as dropped."""
    match = JSON_OBJECT.search(raw or "")
    try:
        data = json.loads(match.group(0)) if match else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise EmbeddingUnavailable("The local model did not return a usable challenge.")
    objections, dropped = [], 0
    for item in (data.get("objections") if isinstance(data.get("objections"), list) else [])[:3]:
        key = item.get("point") if isinstance(item, dict) else None
        why = _clean(item.get("why")) if isinstance(item, dict) else None
        if key in points and why:
            objections.append({"point_id": key, "point": points[key]["point"], "as_of": points[key]["as_of"], "objection": why})
        else:
            dropped += 1
    raw_overlooked = (data.get("overlooked") if isinstance(data.get("overlooked"), list) else [])[:2]
    overlooked = [text for text in map(_clean, raw_overlooked) if text]
    dropped += len(raw_overlooked) - len(overlooked)
    if not objections and not overlooked:
        raise EmbeddingUnavailable("The local model raised no usable objection.")
    return {"objections": objections, "overlooked": overlooked, "dropped": dropped}


def local_reasoner():
    from apps.ml_engine.services.hybrid_intelligence import OllamaReasoner

    class ChallengeReasoner(OllamaReasoner):
        READ_SECONDS = SECONDS  # only this owner-started call waits longer; other AI features keep 30 seconds

    return ChallengeReasoner()


def challenge_packet(packet: dict, *, reasoner=None) -> dict:
    reasoner = reasoner or local_reasoner()
    payload, points = challenge_payload(packet)
    if not points:
        return {"status": "nothing_to_challenge", "detail": "The packet has no screen points to question."}
    raw = reasoner.reason(payload, max_output_tokens=256, deadline=time.monotonic() + SECONDS)
    return {"status": "challenged", "model": reasoner.model, "symbol": packet["symbol"], **parse_challenge(raw, points),
            "limits": ["Hypotheses from a local model, not facts or advice.",
                       "Objections that stated a number were dropped; only the packet's dated figures count.",
                       "Nothing is stored, bought, sold or changed."]}
