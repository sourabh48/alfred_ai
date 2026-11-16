"""Recent public-symbol lookups and bounded automatic reviews; no portfolio mutations."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import ResearchSearch
from .research_packet import research_packet


def summary(packet):
    return {"headline": packet.get("beginner", {}).get("headline", "Evidence is incomplete."),
            "freshness": packet.get("freshness", {}), "source_url": packet["source_url"],
            "good_signs": len(packet.get("bullish", [])), "warning_signs": len(packet.get("bearish", []))}


@transaction.atomic
def remember(user, packet):
    get_user_model().objects.select_for_update().get(pk=user.pk)
    row, _ = ResearchSearch.objects.update_or_create(user=user, symbol=packet["symbol"], defaults={
        "searched_at": timezone.now(), "checked_at": parse_datetime(packet["retrieved_at"]) if packet.get("retrieved_at") else None,
        "summary": summary(packet), "error": ""})
    keep = list(ResearchSearch.objects.filter(user=user).values_list("pk", flat=True)[:20])
    ResearchSearch.objects.filter(user=user).exclude(pk__in=keep).delete()
    return row


def review_recent(user, today):
    from apps.ml_engine.services.task_bots import _item
    items = []
    cutoff = timezone.now() - timedelta(hours=20)
    rows = ResearchSearch.objects.filter(user=user).order_by(F("checked_at").asc(nulls_first=True), "id")
    for row in rows[:3]:
        if row.checked_at and row.checked_at > cutoff:
            continue
        try:
            packet = research_packet(row.symbol)
            data = summary(packet)
            # Updating an existing row cannot resurrect history deleted while the network was busy.
            updated = ResearchSearch.objects.filter(pk=row.pk, user=user, searched_at=row.searched_at).update(
                summary=data, checked_at=parse_datetime(packet["retrieved_at"]) if packet.get("retrieved_at") else None, error="")
            if updated:
                items.append(_item(f"research:{row.pk}:{today}", f"{row.symbol}: research updated",
                    data["headline"] + " " + data["freshness"].get("note", "Evidence may be incomplete."),
                    "/investments/#researchJournalSection"))
        except Exception:
            ResearchSearch.objects.filter(pk=row.pk, user=user, searched_at=row.searched_at).update(error="Online research could not refresh. Previous evidence keeps its original check time.")
    return items
