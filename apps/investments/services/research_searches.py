"""Recent public-symbol lookups and bounded automatic reviews; no portfolio mutations."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Coalesce
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


@transaction.atomic
def _claim_due(user):
    # Reserve the owner's bounded daily batch before making any network requests.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    now = timezone.now()
    cutoff = now - timedelta(hours=20)
    owned = ResearchSearch.objects.filter(user=user)
    slots = max(0, 3 - owned.filter(last_attempt_at__gt=cutoff).count())
    due = owned.filter(
        Q(last_attempt_at__isnull=True) | Q(last_attempt_at__lte=cutoff),
        Q(checked_at__isnull=True) | Q(checked_at__lte=cutoff),
    ).exclude(  # shortcut: a failing symbol waits three days whatever its failure count; add a counter if outages vary a lot
        ~Q(error=""), last_attempt_at__gt=now - timedelta(days=3),
    ).order_by(Coalesce("last_attempt_at", "checked_at").asc(nulls_first=True), "id")
    rows = list(due[:slots])
    owned.filter(pk__in=[row.pk for row in rows]).update(last_attempt_at=now)
    return rows, now


def review_recent(user, today):
    from apps.ml_engine.services.task_bots import _item

    items = []
    rows, attempted_at = _claim_due(user)
    for row in rows:
        current = ResearchSearch.objects.filter(
            pk=row.pk, user=user, searched_at=row.searched_at, last_attempt_at=attempted_at,
        )
        try:
            packet = research_packet(row.symbol)
            data = summary(packet)
            # Updating an existing row cannot resurrect history deleted while the network was busy.
            updated = current.update(
                summary=data, checked_at=parse_datetime(packet["retrieved_at"]) if packet.get("retrieved_at") else None, error="")
            if updated:
                items.append(_item(f"research:{row.pk}:{today}", f"{row.symbol}: research updated",
                    data["headline"] + " " + data["freshness"].get("note", "Evidence may be incomplete."),
                    "/investments/#researchJournalSection"))
        except Exception:
            current.update(error="Online research could not refresh. Previous evidence keeps its original check time.")
    return items
