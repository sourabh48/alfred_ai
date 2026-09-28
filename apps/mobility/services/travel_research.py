"""Bounded, resumable research through the existing verified public-source cache."""
from datetime import date, timedelta
import logging
from uuid import uuid4

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.integrations.services import verified_intelligence
from apps.mobility.models import TravelMessage, TravelPlanningSession, TravelResearchEvidence, TravelResearchSession
from .travel_discovery import candidates_for, value

TERMINAL = {"ready", "failed", "superseded"}
logger = logging.getLogger(__name__)
STAGES = {"queued": "Queued", "destinations": "Researching Destinations", "weather": "Checking Weather",
          "routes": "Checking Routes", "stays": "Checking Stays", "costs": "Comparing Costs",
          "recommendations": "Building Recommendations", "ready": "Ready", "failed": "Failed", "superseded": "Request updated"}


def queue_research(session, deep=False, recheck=False):
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
    run = TravelResearchSession.objects.create(session=session, request=session.state, revision=session.revision,
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
        freshness="fresh" if fresh else "stale" if retrieved else "unknown", finding=finding)
    return evidence_payload(item)


def evidence_payload(item):
    return {"id": item.id, "destination": item.destination, "data_type": item.data_type,
            "source_url": item.source_url, "source_name": item.source_name,
            "retrieved_at": item.retrieved_at.isoformat() if item.retrieved_at else None,
            "valid_until": item.valid_until.isoformat() if item.valid_until else None,
            "confidence": item.confidence, "freshness": "stale" if item.valid_until and item.valid_until <= timezone.now() else item.freshness,
            "finding": item.finding}


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
        options = candidates_for(run.session.user, run.request)
        if run.recheck and run.session.candidates:
            # Recheck existing destinations; don't replace a selected itinerary.
            names = {d["name"] for d in run.session.candidates}
            all_options = candidates_for(run.session.user, run.request, limit=50)
            options = [d for d in all_options if d["name"] in names]
        previous = {d["name"]: d for d in run.session.candidates}
        verified = 0
        changes = []
        for d in options:
            d["sources"] = []
            stage("weather")
            start = value(run.request, "available_start_date")
            end = value(run.request, "available_end_date")
            weather = None
            if start and end and 0 <= (date.fromisoformat(start)-timezone.localdate()).days and (date.fromisoformat(end)-timezone.localdate()).days <= 15:
                try:
                    result = verified_intelligence.weather_snapshot(d["lat"], d["lon"], date.fromisoformat(start), date.fromisoformat(end))
                    ev = result.evidence
                    p = result.payload
                    valid = parse_datetime(ev.get("stale_after") or "")
                    if ev.get("status") == "fresh" and valid and valid > timezone.now() and p.get("average_max_temp") is not None:
                        weather = {**p, "summary": f"Forecast average {p.get('average_min_temp')}–{p.get('average_max_temp')}°C; total rain {p.get('precipitation_total')} mm across your dates.",
                                   "confidence": "LIKELY"}
                        verified += 1
                        d["factors"]["Weather"] = "Rain risk" if (p.get("precipitation_total") or 0) >= 20 else "Forecast available"
                        if (p.get("precipitation_total") or 0) >= 20:
                            d["score"] -= 8
                        old_rain = previous.get(d["name"], {}).get("weather", {}).get("precipitation_total")
                        if run.recheck and old_rain is not None and abs((p.get("precipitation_total") or 0)-old_rain) >= 10:
                            changes.append(f"{d['name']}: forecast rain changed from {old_rain} to {p.get('precipitation_total')} mm across the trip.")
                    d["sources"].append(store_evidence(run, d["name"], "weather", weather or {"summary": "No current forecast could be verified."},
                                                        evidence=ev, confidence="LIKELY"))
                except Exception:
                    d["sources"].append(store_evidence(run, d["name"], "weather", {"summary": "Weather provider unavailable; retry research."}))
            else:
                d["sources"].append(store_evidence(run, d["name"], "weather", {"summary": "Choose dates within the next 16 days for a full-trip forecast; no seasonal estimate is presented as a forecast."}))
            d["weather"] = weather or {"summary": "Current weather for these dates is unverified. Recheck nearer departure.", "confidence": "UNKNOWN"}
            stage("routes")
            d["sources"].append(store_evidence(run, d["name"], "route", {"summary": d["distance_basis"], "distance_km": d["distance_km"],
                "travel_hours": d["travel_hours"]}, confidence="ESTIMATED", source="Alfred town-centre distance estimate"))
            d["sources"].append(store_evidence(run, d["name"], "restrictions", {"summary": d["caution"] + " Official reference provided for checking; its contents have not been fetched."},
                source=d["authority"], url=d["source"]))
            if run.deep:
                try:
                    # Destination alone, never home, names, vehicle or private history.
                    news = verified_intelligence.google_news_search(f"{d['name']} travel road closures permits official")
                    d["sources"].append(store_evidence(run, d["name"], "notices", {"summary": "Related news leads only, not confirmation of access or safety.",
                        "reports": news.payload.get("articles", news.payload.get("items", []))[:5]}, evidence=news.evidence, confidence="UNKNOWN"))
                except Exception:
                    d["sources"].append(store_evidence(run, d["name"], "notices", {"summary": "Public notices search unavailable."}))
            stage("stays")
            d["sources"].append(store_evidence(run, d["name"], "stay", {"summary": f"Suggested area: {d['stay']}. Cost allowance only; no rooms or booking availability verified."},
                confidence="ESTIMATED", source="Alfred budget assumptions"))
            stage("costs")
            d["sources"].append(store_evidence(run, d["name"], "budget", d["budget"], confidence="ESTIMATED", source="Alfred budget assumptions"))
            TravelResearchSession.objects.filter(pk=run_id, lease_token=token).update(
                sources_checked=run.evidence.exclude(retrieved_at=None).count(), candidate_count=len(options), result=options)
        stage("recommendations")
        options.sort(key=lambda d: -d["score"])
        summary = (f"Compared {len(options)} destinations; {verified} current weather forecast(s) available. " if verified else
                   "Preliminary suggestions are ready. I couldn't verify live weather for these dates. ")
        summary += "Road conditions, permits, entry fees and room availability remain unverified."
        if run.recheck:
            summary = (" ".join(changes) if changes else "No meaningful change in the facts I could compare.") + " Unverified facts are still unknown; this is not an all-clear."
        with transaction.atomic():
            current = TravelPlanningSession.objects.select_for_update().get(pk=run.session_id)
            status = "ready" if current.revision == run.revision else "superseded"
            updated = TravelResearchSession.objects.filter(pk=run_id, lease_token=token).update(
                status=status, completed_at=timezone.now(), lease_until=None, summary=summary, changes=changes, result=options)
            if status == "ready" and updated:
                current.candidates = options[:3]
                current.status = "itinerary_ready" if current.itinerary else "destination_selected" if value(current.state, "selected_destination") else "suggestions_ready"
                if current.itinerary:
                    selected = next((c for c in options if c["name"] == current.itinerary.get("destination")), None)
                    if selected:
                        current.itinerary["weather"] = selected["weather"]
                        current.itinerary["sources"] = selected["sources"]
                current.save(update_fields=["candidates", "status", "itinerary", "updated_at"])
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
