"""Bounded, resumable research through the existing verified public-source cache."""
from datetime import date, timedelta
from copy import deepcopy
import logging
from uuid import uuid4

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.mobility.models import TravelMessage, TravelPlanningSession, TravelResearchEvidence, TravelResearchSession
from .travel_discovery import candidates_for, value, fact

TERMINAL = {"ready", "failed", "superseded"}
logger = logging.getLogger(__name__)
STAGES = {"queued": "Queued", "destinations": "Researching Destinations", "weather": "Checking Weather",
          "routes": "Checking Routes", "stays": "Checking Stays", "costs": "Comparing Costs",
          "recommendations": "Building Recommendations", "ready": "Ready", "failed": "Failed", "superseded": "Request updated"}


def queue_research(session, deep=False, recheck=False, force=False):
    active = session.research_runs.exclude(status__in=TERMINAL).filter(revision=session.revision).first()
    if active:
        if deep and not active.deep:
            if active.status == "queued":
                active.deep = True
                active.save(update_fields=["deep"])
                return active
            session.revision += 1
            session.save(update_fields=["revision"])
        else:
            return active
    request = deepcopy(session.state)
    if force:
        request["force_refresh"] = fact(True, "explicit_refresh")
    run = TravelResearchSession.objects.create(session=session, request=request, revision=session.revision,
                                              deep=deep, recheck=recheck)
    session.status = "researching"
    session.save(update_fields=["status", "updated_at"])
    # Database row is the outbox. Broker outages leave it queued for the sweeper.
    transaction.on_commit(lambda: dispatch(run.id))
    return run


def dispatch(run_id):
    from apps.mobility.tasks import research_travel
    try:
        if hasattr(research_travel, "queued"):
            research_travel.delay(run_id)
        else:
            # Bounded broker handoff; internet work is never run in this request.
            with research_travel.app.connection_for_write(connect_timeout=1) as connection:
                research_travel.apply_async(args=[run_id], connection=connection, retry=False)
    except Exception:
        TravelResearchSession.objects.filter(pk=run_id, status="queued").update(
            summary="Saved and queued. Waiting for the background worker; retry is automatic.")


def store_evidence(run, destination, kind, finding, *, evidence=None, confidence="UNKNOWN", source="Not verified", url=""):
    evidence = evidence or {}
    retrieved = parse_datetime(evidence.get("fetched_at") or "")
    valid = parse_datetime(evidence.get("stale_after") or "")
    fresh = evidence.get("status") == "fresh" and retrieved and valid and valid > timezone.now()
    if evidence and not fresh:
        confidence = "UNKNOWN"
    item = TravelResearchEvidence.objects.create(
        research=run, destination=destination, data_type=kind, source_url=evidence.get("source_url", url),
        source_name=evidence.get("source_name", source), retrieved_at=retrieved,
        valid_until=valid, confidence=confidence,
        freshness="RECENTLY_VERIFIED" if fresh else "CACHED" if retrieved else "ESTIMATED" if confidence == "ESTIMATED" else "UNKNOWN", finding=finding)
    return evidence_payload(item)


def evidence_payload(item):
    return {"id": item.id, "destination": item.destination, "data_type": item.data_type,
            "source_url": item.source_url, "source_name": item.source_name,
            "retrieved_at": item.retrieved_at.isoformat() if item.retrieved_at else None,
            "valid_until": item.valid_until.isoformat() if item.valid_until else None,
            "confidence": "UNKNOWN" if item.valid_until and item.valid_until <= timezone.now() else item.confidence,
            "freshness": "CACHED" if item.valid_until and item.valid_until <= timezone.now() else item.freshness,
            "provider": item.provider, "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            "status": item.status, "error": item.error, "response_hash": item.response_hash,
            "finding": item.finding}


def store_provider_evidence(run, destination, result):
    kind = {"routing":"route", "hotels":"stay", "permits":"restrictions"}.get(result.category,result.category)
    item = TravelResearchEvidence.objects.create(research=run, destination=destination, data_type=kind,
        provider=result.provider, source_name=result.provider, source_url=result.source_url,
        retrieved_at=parse_datetime(result.retrieved_at or ""), verified_at=parse_datetime(result.verified_at or ""),
        valid_until=parse_datetime(result.expires_at or ""), response_hash=result.response_hash,
        request_parameters=result.request_parameters, status=result.status, error=result.error,
        confidence=result.confidence, freshness=result.freshness,
        finding={**result.payload,"attribution":result.attribution,"fallback":result.fallback})
    return evidence_payload(item)


def run_research(run_id):
    token = str(uuid4())
    now = timezone.now()
    # Conditional UPDATE provides a cross-process lease on SQLite and Postgres.
    acquired = TravelResearchSession.objects.filter(pk=run_id).exclude(status__in=TERMINAL).filter(
        Q(lease_until__isnull=True) | Q(lease_until__lt=now)).update(
        lease_token=token, lease_until=now+timedelta(minutes=4), started_at=now, status="destinations")
    if not acquired:
        return {"status": "already_claimed_or_finished"}
    run = TravelResearchSession.objects.select_related("session__user").get(pk=run_id)

    def stage(name):
        if not TravelResearchSession.objects.filter(pk=run_id, lease_token=token).update(
                status=name, updated_at=timezone.now(), lease_until=timezone.now()+timedelta(minutes=4)):
            raise RuntimeError("Research lease expired.")

    try:
        from .travel.research import enrich_candidate, research_candidates
        from .travel.discovery import remember
        preliminary = candidates_for(run.session.user, run.request, limit=50)
        options = research_candidates(run.session.user, run.request, preliminary)[:3]
        if run.recheck and run.session.candidates and not value(run.request, "requested_destination"):
            options = run.session.candidates
        previous = {d["name"]: d for d in run.session.candidates}
        verified, changes, researched = 0, [], []
        for destination in options:
            stage("weather")
            d, results = enrich_candidate(run.session.user, run.request, destination)
            d["sources"] = [store_provider_evidence(run, d["name"], result) for result in results]
            d["sources"].append(store_evidence(run, d["name"], "budget", d["budget"],
                confidence="ESTIMATED", source="ALFRED budget formulas"))
            weather = d.get("weather_result", {})
            if weather.get("success") and not weather.get("stale"):
                verified += 1
            old_rain = previous.get(d["name"], {}).get("weather", {}).get("precipitation_total")
            rain = d["weather"].get("precipitation_total")
            if run.recheck and rain is not None and old_rain is not None and abs(rain-old_rain) >= 10:
                changes.append(f"{d['name']}: forecast rain changed from {old_rain} to {rain} mm across the trip.")
            researched.append(d)
            stage("costs")
        options = researched
        stage("recommendations")
        options.sort(key=(lambda d: d["budget"]["expected"]) if value(run.request,"sort_by") == "cost" else (lambda d: -d["score"]))
        summary = (f"Compared {len(options)} destinations; {verified} current weather forecast(s) available. " if verified else
                   "Preliminary suggestions are ready. I couldn't verify live weather for these dates. ")
        summary += "Road conditions, permits, entry fees and room availability remain unverified."
        if run.recheck:
            summary = (" ".join(changes) if changes else "No meaningful change in the facts I could compare.") + " Unverified facts are still unknown; this is not an all-clear."
        with transaction.atomic():
            current = TravelPlanningSession.objects.select_for_update().get(pk=run.session_id)
            status = "ready" if current.revision == run.revision else "superseded"
            updated = TravelResearchSession.objects.filter(pk=run_id, lease_token=token).update(
                status=status, completed_at=timezone.now(), lease_until=None, summary=summary, changes=changes, result=options,
                candidate_count=len(options), sources_checked=run.evidence.exclude(retrieved_at=None).count())
            if status == "ready" and updated:
                current.candidates = options[:3]
                current.status = "ready" if current.itinerary else "researched"
                if value(current.state,"requested_destination") and len(options) == 1 and not current.itinerary:
                    from .travel_itinerary import build_itinerary
                    current.state["selected_destination"] = fact(options[0]["name"])
                    current.itinerary = build_itinerary(current.state,options[0])
                    current.status = "ready"
                for candidate in current.candidates:
                    remember(current.user, candidate, "shown")
                    for place in candidate.get("places_result", {}).get("payload", {}).get("places", []):
                        remember(current.user, place, "shown")
                if current.itinerary:
                    selected = next((c for c in options if c["name"] == current.itinerary.get("destination")), None)
                    if selected:
                        current.itinerary["weather"] = selected["weather"]
                        current.itinerary["sources"] = selected["sources"]
                        for key in ("route_result", "weather_result", "places_result", "permit_result", "hotels_result", "flights_result", "trains_result", "buses_result", "discovery_result", "weather_proposals", "map", "quality", "mode_comparison", "web_research", "external_links"):
                            current.itinerary[key] = selected.get(key, {})
                        current.itinerary["route"].update(distance_km_one_way=selected.get("distance_km"),hours_one_way=selected.get("travel_hours"),note=selected["distance_basis"])
                        if current.itinerary.get("edits"):
                            current.itinerary["budget"]["recheck_note"] = "Research updated; your edited budget allowances were retained. Review changed route/prices before saving."
                        else:
                            current.itinerary["budget"] = selected["budget"]
                            days = current.itinerary["days"]
                            for i, day in enumerate(days):
                                total = selected["budget"]["expected"]
                                day["estimated_cost"] = total//len(days)+(total%len(days) if i == len(days)-1 else 0)
                current.save(update_fields=["candidates", "status", "itinerary", "state", "updated_at"])
                if current.plan_id and current.plan.status == "researching":
                    current.plan.status = "suggestions_ready"
                    current.plan.save(update_fields=["status","updated_at"])
                TravelMessage.objects.create(session=current, role="assistant", text=summary,
                                             chips=["Compare destinations", "Research thoroughly", "Something cheaper"])
        return {"status": status, "candidate_count": len(options)}
    except Exception:
        logger.exception("Travel research run %s failed", run_id)
        TravelResearchSession.objects.filter(pk=run_id, lease_token=token).update(status="failed", lease_until=None,
            completed_at=timezone.now(), error="Research was interrupted. Your request is saved; retry research.")
        return {"status": "failed"}
