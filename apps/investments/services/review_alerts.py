"""Opted-in local record-review reminders, never price or trading signals."""
from copy import deepcopy
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.ml_engine.services.persistent_memory import _owner


def expire_review_alerts(policy, now):
    """Shared by on-access checks and the existing private-vault expiry job."""
    removed=0
    for identity, item in list(policy['items'].items()):
        created=datetime.fromisoformat(item['created_at'])
        if created.tzinfo is None or created>now or item['status'] not in ('unread','read','dismissed','resolved'):
            raise RuntimeError('Reminder verification failed.')
        if created<=now-timedelta(days=90):
            del policy['items'][identity]
            removed+=1
    return removed


class AlertConflict(APIException):
    status_code = 409
    default_detail = 'Reminders changed. Reload before trying again.'


class RecordReviewAlerts:
    KEY = 'investment_record_review'
    LIMIT = 20

    def __init__(self, store):
        self.store = store

    def run(self, user, payload=None):
        from ..models import Investment
        now = timezone.now()
        # No amounts or asset names are copied into persistent reminder state.
        holdings = {str(row.pk): row for row in Investment.objects.filter(user=user).order_by('pk')[:self.LIMIT+1]}
        owner = _owner(user)
        with self.store._transaction() as db:
            state = self.store._sync_state(db, owner)
            saved = state.get(self.KEY)
            policy = deepcopy(saved if saved is not None else dict(enabled=False, days=30, revision=0, checked_at=None, items={}))
            if not isinstance(policy, dict) or type(policy.get('enabled')) is not bool or type(policy.get('revision')) is not int or policy.get('days') not in (7,30,90) or not isinstance(policy.get('items'),dict) or len(policy['items'])>self.LIMIT:
                raise RuntimeError('Reminder policy verification failed.')
            missing=set(policy['items'])-set(holdings)
            holdings.update({str(row.pk):row for row in Investment.objects.filter(user=user,pk__in=missing)})
            expire_review_alerts(policy,now)
            for identity, item in list(policy['items'].items()):
                row = holdings.get(identity)
                if not row or row.updated_at.isoformat()!=item['source_updated_at'] or row.updated_at>now-timedelta(days=policy['days']):
                    item['status']='resolved'
            if payload is not None:
                if type(payload.get('revision')) is not int or payload['revision']!=policy['revision']:
                    raise AlertConflict()
                action = payload.get('action')
                if action=='configure':
                    if set(payload)-{'action','revision','enabled','days','consent'} or type(payload.get('enabled')) is not bool or type(payload.get('days')) is not int or payload['days'] not in (7,30,90):
                        raise ValidationError('Choose a reminder policy of 7, 30 or 90 days.')
                    if payload['enabled'] and payload.get('consent') is not True:
                        raise ValidationError('Explicit local reminder consent is required.')
                    policy.update(enabled=payload['enabled'], days=payload['days'])
                    for identity, item in policy['items'].items():
                        if identity in holdings and holdings[identity].updated_at>now-timedelta(days=policy['days']):
                            item['status']='resolved'
                    if not policy['enabled']:
                        policy['items']={}
                        policy['checked_at']=None
                elif action=='evaluate':
                    if set(payload)!={'action','revision'} or not policy['enabled']:
                        raise ValidationError('Enable local reminders before checking records.')
                    if len(holdings)>self.LIMIT:
                        raise ValidationError('Local reminders support at most 20 holdings; no partial check was saved.')
                    for identity, row in holdings.items():
                        if row.updated_at <= now-timedelta(days=policy['days']):
                            item=policy['items'].get(identity)
                            if not item or item['status']=='resolved':
                                policy['items'][identity]=dict(source_updated_at=row.updated_at.isoformat(),created_at=now.isoformat(),status='unread')
                    # Prefer current reminders when the bounded history fills up.
                    policy['items']=dict(sorted(policy['items'].items(),key=lambda pair:(pair[1]['status']=='resolved',pair[1]['created_at']),reverse=False)[:self.LIMIT])
                    policy['checked_at']=now.isoformat()
                elif action in ('read','dismiss'):
                    identity=str(payload.get('id'))
                    item=policy['items'].get(identity)
                    if set(payload)!={'action','revision','id'} or type(payload.get('id')) is not int or not item or item['status'] not in ('unread','read') or not policy['enabled']:
                        raise AlertConflict()
                    item['status']='read' if action=='read' else 'dismissed'
                else:
                    raise ValidationError('Choose configure, evaluate, read or dismiss.')
            if payload is not None or saved is not None and saved!=policy:
                policy['revision']+=1
                state[self.KEY]=policy
                self.store._write_sync_state(db,owner,state)
            items=[]
            for identity, item in policy['items'].items():
                row=holdings.get(identity)
                if row:
                    items.append(dict(id=row.pk,name=row.asset_name,**item,
                        url=f'/ai/financial-records/investment/{row.pk}/'))
            return dict(**{key:value for key,value in policy.items() if key!='items'},items=items,
                limit=self.LIMIT,retention_days=90,unassessed_records=sum(row.updated_at>now for row in holdings.values()),
                limitations='Record edit dates only; not verified valuation, market freshness or price alerts. Checks run only on request. No email, background delivery, trading or monetary thresholds.')
