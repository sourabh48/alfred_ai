from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from alfred_ai.background import shared_task


@shared_task
def research_travel(run_id):
    from .services.travel_research import run_research
    return run_research(run_id)


@shared_task
def resume_travel_research():
    from .models import TravelResearchSession
    from .services.travel_research import TERMINAL, dispatch
    now = timezone.now()
    due = TravelResearchSession.objects.exclude(status__in=TERMINAL).filter(
        Q(lease_until__lt=now) | Q(lease_until=None, created_at__lt=now-timedelta(seconds=30)))
    ids = list(due.values_list("id", flat=True)[:20])
    for run_id in ids:
        dispatch(run_id)
    return {"resumed": len(ids)}
