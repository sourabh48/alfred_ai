"""Providers whose terms allow keeping their data only while the app needs it to run (Amadeus Travel Builder terms,
section 4: no permanent or cached copies beyond what the application needs to run efficiently; checked 2026-11-19).

Every 15 minutes, expired offers from these providers are removed wherever ALFRED saved them: the shared provider
cache, research evidence, planning chats and saved plans. The search itself (airports, dates, travellers) stays, so
the person can search again for current fares.
"""
from __future__ import annotations

from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.utils import timezone
from django.utils.dateparse import parse_datetime

SHORT_KEEP = ("amadeus", "amadeus_airports")
NOTE = "Live fares from this source are kept only briefly; search again for current fares."


def _expired(stamp, now) -> bool:
    when = parse_datetime(str(stamp or ""))
    return when is None or when <= now  # a missing or unreadable expiry counts as expired


def scrub(value, now) -> bool:
    """Empty every expired short-keep provider result inside a saved JSON value, in place. True if anything changed."""
    changed = False
    if isinstance(value, dict):
        payload = value.get("payload")
        if value.get("provider") in SHORT_KEEP and isinstance(payload, dict) and payload.get("options") and _expired(value.get("expires_at"), now):
            value["payload"] = {"options": [], "coverage": payload.get("coverage", ""), "removed": NOTE}
            changed = True
        for item in value.values():
            changed |= scrub(item, now)
    elif isinstance(value, list):
        for item in value:
            changed |= scrub(item, now)
    return changed


def purge(now=None) -> int:
    """Remove expired short-keep offers everywhere they were saved; returns how many records changed."""
    from apps.integrations.models import VerifiedExternalInsight
    from apps.mobility.models import TravelPlan, TravelPlanningSession, TravelResearchEvidence, TravelResearchSession

    now = now or timezone.now()
    changed = VerifiedExternalInsight.objects.filter(scope="travel_provider", source_name__in=SHORT_KEEP, stale_after__lte=now).delete()[0]
    for item in TravelResearchEvidence.objects.filter(Q(valid_until__lte=now) | Q(valid_until__isnull=True), provider__in=SHORT_KEEP):
        if item.finding.get("options"):
            item.finding = {"options": [], "attribution": item.finding.get("attribution", ""), "removed": NOTE}
            item.save(update_fields=["finding"])
            changed += 1
    for model, fields in ((TravelPlanningSession, ("state", "candidates", "itinerary")), (TravelResearchSession, ("result",)),
                          (TravelPlan, ("planning_state", "itinerary"))):
        mentions = Q()
        for name in fields:  # only rows whose saved JSON names a short-keep provider are read
            mentions |= Q(**{f"{name}_text__contains": '"amadeus"'})
        rows = model.objects.annotate(**{f"{name}_text": Cast(name, TextField()) for name in fields}).filter(mentions)
        for row in rows:
            touched = [name for name in fields if scrub(getattr(row, name), now)]
            if touched:
                row.save(update_fields=touched)
                changed += 1
    return changed
