"""Reviewed restart of an unavailable timeline, retaining its exact private source."""
from datetime import datetime
from hashlib import sha256
import json
from uuid import uuid4

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from apps.ml_engine.services.assistant_actions import ActionError, ActionConflict, PROPOSAL_TTL, _digest, _identity
from apps.ml_engine.services.persistent_memory import _owner
from apps.reports.models import OperationalLog
from ..models import CareerJobAnalysis
from .application_tracker import apply_change, follow_up_status

SCOPE = 'career_history_review'
MAX_ARCHIVES = 5


def _json(value, limit=128*1024):
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(encoded.encode()) > limit:
            raise ValueError()
        return encoded
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ActionError('This history exceeds the supported review bounds. No records were changed.') from None


def _owned(user, pk):
    _owner(user)
    return get_object_or_404(CareerJobAnalysis, pk=pk, user=user, user__is_active=True)


def _revision(row):
    # Fingerprint all source fields without writing private text or low-entropy dates to audit logs.
    return _digest([row.pk, row.user_id, row.updated_at.isoformat(),
                    sha256(_json(row.extracted_payload, 2*1024*1024).encode()).hexdigest()])


def _source(row):
    payload = row.extracted_payload
    if not isinstance(payload, dict):
        raise ActionError('The saved opportunity requires a separate source review. No records were changed.')
    archives = payload.get('application_history_recoveries', [])
    if not isinstance(archives, list) or len(archives) > MAX_ARCHIVES:
        raise ActionError('The retained history archive requires a separate review.')
    source = dict(application=payload.get('application'), recoveries=archives)
    _json(source)
    return source


def inspect(user, pk):
    row = _owned(user, pk)
    source = _source(row)
    return dict(revision=_revision(row), **source,
        can_recover=len(source['recoveries'])<MAX_ARCHIVES and len(_json(source['application']).encode())<=16*1024
            and follow_up_status(source['application'], today=timezone.localdate())['status']=='unavailable')


def _timeline(fields):
    if (not isinstance(fields, dict) or set(fields) != {'stage', 'on'}
            or not isinstance(fields['stage'], str) or not isinstance(fields['on'], str)
            or len(fields['on']) != 10):
        raise ActionError('Choose a stage and an explicit date in YYYY-MM-DD form.')
    try:
        timeline = apply_change(None, fields, today=timezone.localdate())
        if timeline['history'][0]['on'] != fields['on']:
            raise ValueError()
        return timeline
    except ValueError:
        raise ActionError('Choose a valid stage and an explicit date that is not in the future.') from None


def _records(user):
    return OperationalLog.objects.filter(user=user, module='career', scope=SCOPE)


@transaction.atomic
def prepare(user, pk, revision, fields):
    row = _owned(user, pk)
    if not isinstance(revision, str) or not constant_time_compare(_revision(row), revision):
        raise ActionConflict('This opportunity changed. Reload its retained history before reviewing again.')
    source = _source(row)
    if (len(source['recoveries']) >= MAX_ARCHIVES
            or follow_up_status(source['application'], today=timezone.localdate())['status']!='unavailable'):
        raise ActionConflict('Recovery is unavailable for this timeline. Review its current history or use normal stage editing.')
    _json(source['application'], 16*1024)
    timeline = _timeline(fields)
    # Leave room for the exact retained source and the new review metadata.
    _json([source, dict(previous_application=source['application'], fields=fields)])
    now = timezone.now()
    if _records(user).filter(event_type='career_history_pending', created_at__gt=now-PROPOSAL_TTL).count() >= 20:
        raise ActionError('Too many pending reviews. Cancel one or wait ten minutes.')
    identity = uuid4().hex
    expires = now+PROPOSAL_TTL
    OperationalLog.objects.create(user=user, module='career', category='api', scope=SCOPE,
        event_type='career_history_pending', message='Career timeline recovery awaiting owner confirmation.',
        payload=dict(proposal_id=identity, state='pending', revision=revision, expires_at=expires.isoformat(),
                     target_binding=_digest([user.pk, pk, identity]),
                     binding=_digest([user.pk, pk, identity, fields])))
    return dict(proposal_id=identity, expires_at=expires.isoformat(), fields=fields, timeline=timeline,
                detail='Start a new owner-reported timeline. The exact prior history will be retained; prior follow-ups do not become part of the new timeline.')


@transaction.atomic
def confirm(user, pk, identity, fields, confirmed):
    _identity(identity)
    if confirmed is not True:
        raise ActionError('Explicit confirmation of the reviewed timeline is required.')
    _owner(user)
    _timeline(fields)
    records = _records(user).filter(payload__proposal_id=identity)
    # Reuse the existing action claim order: SQLite serializes writes before source reads.
    claimed = records.filter(event_type='career_history_pending').update(event_type='career_history_claimed')
    record = records.select_for_update().first()
    if record is None:
        raise ActionError('This review is unavailable. Review the retained history again.')
    payload = record.payload
    if not constant_time_compare(payload['binding'], _digest([user.pk, pk, identity, fields])):
        raise ActionError('The reviewed values changed. Make a new review.')
    row = _owned(user, pk)
    if not claimed:
        if payload['state']=='confirmed':
            return dict(already_applied=True, analysis_id=pk)
        raise ActionConflict('This review was cancelled. Nothing was changed.')
    if timezone.now() >= datetime.fromisoformat(payload['expires_at']):
        raise ActionConflict('This review expired. Review the retained history again.')
    if not constant_time_compare(_revision(row), payload['revision']):
        raise ActionConflict('This opportunity changed after review. Reload its retained history.')
    source = _source(row)
    if len(source['recoveries']) >= MAX_ARCHIVES:
        raise ActionConflict('The archive limit was reached. No history was removed.')
    now = timezone.now()
    archive = dict(proposal_id=identity, reviewed_at=now.isoformat(), previous_application=source['application'], fields=fields)
    _json([source, archive])
    timeline = _timeline(fields)
    timeline['history_recovery_id'] = identity
    changed = CareerJobAnalysis.objects.filter(pk=pk, user=user, updated_at=row.updated_at,
        extracted_payload=row.extracted_payload).update(updated_at=now, extracted_payload={**row.extracted_payload,
            'application':timeline, 'application_history_recoveries':source['recoveries']+[archive]})
    if changed != 1:
        raise ActionConflict('This opportunity changed after review. Reload its retained history.')
    record.payload = {**payload, 'state':'confirmed', 'confirmed_at':now.isoformat()}
    record.event_type = 'career_history_confirmed'
    record.message = 'Owner-confirmed timeline recovery applied once; prior history retained privately.'
    record.save(update_fields=['payload', 'event_type', 'message'])
    return dict(already_applied=False, analysis_id=pk)


@transaction.atomic
def cancel(user, pk, identity):
    _identity(identity)
    _owned(user, pk)
    records = _records(user).filter(payload__proposal_id=identity, payload__target_binding=_digest([user.pk, pk, identity]))
    records.filter(event_type='career_history_pending').update(event_type='career_history_cancelled')
    record = records.select_for_update().first()
    if record is None:
        raise ActionError('This review is unavailable.')
    if record.payload['state']=='confirmed':
        raise ActionConflict('This recovery was already saved. Reload Career.')
    record.payload = {**record.payload, 'state':'cancelled'}
    record.save(update_fields=['payload'])
    return dict(cancelled=True)
