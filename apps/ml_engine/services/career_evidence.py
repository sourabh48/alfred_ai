"""Bounded owned application progress; no resume text, model calls or record changes."""
from django.utils import timezone

from apps.career.models import CareerJobAnalysis
from apps.career.services.application_tracker import STAGES, follow_up_status
from .canonical_evidence import _digest

SCAN_LIMIT = 300


def application_source(user):
    today = timezone.localdate()
    records = CareerJobAnalysis.objects.filter(user=user).order_by('-updated_at', '-pk')
    total = records.count()
    rows = list(records.values('id', 'company', 'job_title', 'updated_at', 'extracted_payload__application')[:SCAN_LIMIT])
    counts = dict.fromkeys(STAGES, 0)
    untracked = 0
    recent = []
    for row in rows:
        application = row['extracted_payload__application']
        application = application if isinstance(application, dict) else {}
        stage = application.get('stage')
        if not isinstance(stage, str) or stage not in STAGES:
            untracked += 1
            stage = None
        else:
            counts[stage] += 1
        if len(recent) < 3:
            label = ' · '.join(str(row[key] or 'Not recorded')[:100] for key in ('company', 'job_title'))
            recent.append(f"Opportunity #{row['id']} · {label} · {stage or 'No valid stage recorded'} · "
                          f"{follow_up_status(application, today=today)['detail'] if stage else 'Follow-up unavailable'}")
    data = dict(follow_up_dates_as_of=today.isoformat(), total_saved_opportunities=total, opportunities_scanned=len(rows),
        opportunities_outside_scan=max(0, total-len(rows)), no_valid_stage_recorded=untracked,
        progress=[f'{stage}: {count}' for stage, count in counts.items()], recent_opportunities=recent,
        provenance='Owned Career saved job analyses and their recorded application stages',
        limitations=['Stages and sent follow-ups are recorded reports, not independent employer or submission verification.',
            'Counts cover at most the 300 most recently updated saved opportunities; recent details show at most three.',
            'No salary, contacts, resume text or job-description text is included. Missing dates are not inferred.',
            'This snapshot is page-only. Review or update records in Career.'])
    return dict(ref='career-applications', classification='recorded_career_progress', url='/career/',
        as_of=today.isoformat(), revision=_digest(dict(owner=user.pk, data=data,
            revisions=[(row['id'], row['updated_at']) for row in rows], day=today)), data=data)
