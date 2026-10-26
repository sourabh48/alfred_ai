"""Owner-reviewed public references, never independent road or legal clearance."""
from datetime import timedelta, timezone as datetime_timezone
from hashlib import sha256
import json
import re
from urllib.parse import urlsplit

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import Throttled, ValidationError

from alfred_ai.services.public_http import normalized_link
from apps.mobility.models import TravelResearchEvidence
from ..travel_discovery import value


KIND = "motorcycle_restriction"
CLAIMS = ("PROHIBITED", "CONDITIONAL")
NOTE = ("VERIFIED means your reviewed reference for this exact route and trip context, not independent source authentication. "
    "Car routing and highway avoidance never establish motorcycle legality. Recheck rules and dates with the authority; "
    "this reference is not whole-route or future travel clearance.")


def _timestamp(raw):
    if not isinstance(raw, str) or len(raw) > 80:
        return None
    try:
        parsed = parse_datetime(str(raw or ""))
    except (ValueError, TypeError, OverflowError):
        return None
    return parsed.astimezone(datetime_timezone.utc) if parsed and timezone.is_aware(parsed) else None


def _source(raw):
    if not isinstance(raw, str) or len(raw) > 1000:
        return ""
    url = normalized_link(raw)
    host = urlsplit(url).hostname or ""
    # shortcut: Indian government reference hosts only; expand after source-policy review.
    return url if host.endswith((".gov.in", ".nic.in")) else ""


def _scope(session, candidate, route_id):
    inputs = {k: value(session.state, k) for k in ("origin", "transport_mode", "avoid_expressways", "avoid_tolls",
        "available_start_date", "available_end_date", "trip_duration")}
    return sha256(json.dumps({"inputs": inputs, "route_id": route_id,
        "destination": candidate["name"]}, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _identity(finding, source, checked, expiry):
    return sha256(json.dumps([finding, source, checked.isoformat(), expiry.isoformat()], sort_keys=True).encode()).hexdigest()


def _current(candidate, route, now):
    result = candidate.get("route_result", {})
    checked, expiry = (_timestamp(result.get(k)) for k in ("retrieved_at", "expires_at"))
    return bool(result.get("success") and not result.get("stale") and normalized_link(result.get("source_url", ""))
        and checked and expiry and checked <= now < expiry and route.get("profile") == "driving-car")


def record_restriction(session, data):
    required = {"candidate_index", "route_id", "restriction", "road", "quote", "source_url", "checked_at", "expires_at", "reviewed"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValidationError({"detail": "Supply only the displayed route and supported public-reference fields."})
    index, route_id = data["candidate_index"], data["route_id"]
    if (type(index) is not int or not 0 <= index < len(session.candidates) or not isinstance(route_id, str)
            or not re.fullmatch(r"[0-9a-f]{64}", route_id) or value(session.state, "transport_mode") != "ride"):
        raise ValidationError({"detail": "Choose a displayed motorcycle-trip route."})
    candidate = session.candidates[index]
    route = next((r for r in candidate.get("route_result", {}).get("payload", {}).get("routes", []) if r.get("route_id") == route_id), None)
    now = timezone.now()
    if not route or not _current(candidate, route, now):
        raise ValidationError({"detail": "The route changed or expired. Recheck before recording a reference."})
    run = session.research_runs.first()
    if run and run.status not in ("ready", "failed", "superseded"):
        raise ValidationError({"detail": "Wait for current route research before recording a reference."})
    source = _source(data["source_url"])
    checked, expiry = (_timestamp(data[k]) for k in ("checked_at", "expires_at"))
    if (data["reviewed"] is not True or data["restriction"] not in CLAIMS or not source
            or not checked or not expiry or not checked <= now < expiry <= checked+timedelta(hours=24)
            or any(not isinstance(data[k], str) or not 1 <= len(data[k].strip()) <= limit for k, limit in (("road", 160), ("quote", 1200)))):
        raise ValidationError({"detail": "Review a prohibition or conditional rule, quote its public government reference, and set a current check/expiry within 24 hours. Permission or whole-route clearance is unsupported."})
    if not run:
        raise ValidationError({"detail": "Research this conversation's route before recording a reference."})
    finding = {"route_id": route_id, "route_scope": _scope(session, candidate, route_id), "reviewer_id": session.user_id,
        "restriction": data["restriction"], "road": data["road"].strip(), "quote": data["quote"].strip()}
    identity = _identity(finding, source, checked, expiry)
    owned = TravelResearchEvidence.objects.filter(research__session=session, data_type=KIND)
    existing = owned.filter(response_hash=identity, status="owner_reviewed").first()
    if existing:
        return existing
    if owned.count() >= 100 or owned.filter(finding__route_scope=finding["route_scope"]).count() >= 20:
        raise Throttled(detail="This conversation's retained-reference limit is reached. Existing evidence is preserved; withdrawal remains available.")
    return TravelResearchEvidence.objects.create(research=run, destination=candidate["name"], data_type=KIND,
        provider="owner_reviewed_reference", source_name="Owner-reviewed government reference", source_url=source,
        retrieved_at=checked, valid_until=expiry, verified_at=now, confidence="UNKNOWN", freshness="USER_PROVIDED",
        status="owner_reviewed", finding=finding, response_hash=identity)


def restriction_context(session, payload):
    rows = list(TravelResearchEvidence.objects.filter(research__session=session, data_type=KIND).order_by("-pk")[:100])
    now = timezone.now()
    for candidate in [*payload.get("candidates", []), payload.get("itinerary", {})]:
        if not candidate:
            continue
        candidate["motorcycle_restrictions"] = {}
        for route in candidate.get("route_result", {}).get("payload", {}).get("routes", [])[:3]:
            route_id = route.get("route_id")
            if not isinstance(route_id, str) or not re.fullmatch(r"[0-9a-f]{64}", route_id):
                continue
            # Itinerary uses destination in place of the candidate's name.
            target = candidate if "name" in candidate else {**candidate, "name": candidate.get("destination")}
            binding = _scope(session, target, route_id)
            proofs = []
            for row in rows:
                finding = row.finding
                if (not isinstance(finding, dict) or finding.get("route_scope") != binding or finding.get("route_id") != route_id
                        or finding.get("reviewer_id") != session.user_id or row.provider != "owner_reviewed_reference"
                        or row.status not in ("owner_reviewed", "withdrawn") or finding.get("restriction") not in CLAIMS
                        or not _source(row.source_url) or not row.retrieved_at or not row.valid_until or not row.verified_at
                        or not row.retrieved_at <= row.verified_at <= now or not row.retrieved_at < row.valid_until <= row.retrieved_at+timedelta(hours=24)
                        or any(not isinstance(finding.get(k), str) or not 1 <= len(finding[k].strip()) <= limit for k, limit in (("road", 160), ("quote", 1200)))
                        or row.response_hash != _identity(finding, row.source_url, row.retrieved_at, row.valid_until)):
                    continue
                proofs.append({"id": row.pk, "status": "UNKNOWN" if row.status == "withdrawn" else "STALE" if row.valid_until <= now else "VERIFIED",
                    "withdrawn": row.status == "withdrawn", "restriction": finding["restriction"], "road": finding["road"], "quote": finding["quote"],
                    "source_url": row.source_url, "checked_at": row.retrieved_at.isoformat(), "expires_at": row.valid_until.isoformat()})
            fresh = {p["restriction"] for p in proofs if p["status"] == "VERIFIED"}
            status = ("UNAVAILABLE" if not _current(candidate, route, now) else "UNKNOWN" if value(session.state, "transport_mode") != "ride" else
                "VERIFIED" if len(fresh) == 1 else "UNKNOWN" if len(fresh) > 1 else "STALE" if any(p["status"] == "STALE" for p in proofs) else "UNKNOWN")
            candidate["motorcycle_restrictions"][route_id] = {"status": status, "restriction": next(iter(fresh)) if status == "VERIFIED" else None,
                "conflicting": len(fresh) > 1, "motorcycle_legal": "UNKNOWN", "independent_authentication": False,
                "basis": "owner_reviewed_reference", "note": NOTE, "evidence": proofs}
        selected = candidate.get("selected_route_id") or candidate.get("route", {}).get("selected_route_id")
        candidate["motorcycle_restriction_status"] = candidate["motorcycle_restrictions"].get(selected, {}).get("status",
            "UNKNOWN" if candidate["motorcycle_restrictions"] else "UNAVAILABLE")
    return payload
