"""Owned investment-document drafts; extraction cannot post or overwrite canonical investments."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from math import isfinite
from uuid import uuid4

from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from apps.expenses.services.statement_evidence import file_reference
from apps.reports.services import operational_logging_service
from ..models import Investment, InvestmentImportDocument
from ..money import investment_money
from ..serializers import InvestmentSerializer
from .document_evidence import capture_import

FIELDS = ('asset_name', 'asset_type', 'institution', 'account_number', 'invested_amount',
          'current_value', 'monthly_sip', 'currency', 'annual_return_rate')
MONEY = ('invested_amount', 'current_value', 'monthly_sip')
PAGE_SIZE = 10
SALT = 'alfred.investment-document-review.v1'


class InvestmentReviewConflict(ValueError):
    pass


def _json(value):
    return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return sha256(_json(value).encode()).hexdigest()


def _review(document):
    review = (document.extracted_payload or {}).get('import_review')
    if not isinstance(review, dict) or review.get('state') not in ('pending', 'confirmed'):
        raise InvestmentReviewConflict('Retry the original source to prepare a review.')
    return review


def _identity(row):
    return tuple(str(row.get(key) or '').strip().casefold() for key in ('asset_name', 'institution', 'account_number'))


def _matches(user, row):
    name, institution, account = _identity(row)
    return Investment.objects.filter(user=user, asset_name__iexact=name,
        institution__iexact=institution, account_number__iexact=account) if name else Investment.objects.none()


@transaction.atomic
def stage_investment_document(*, user, parsed, upload_file=None, existing=None):
    rows = parsed.get('investments') or []
    if not isinstance(rows, list) or len(rows) > 100 or any(not isinstance(row, dict) for row in rows):
        raise ValueError('The source exceeds the supported investment review size.')
    original = json.loads(_json(rows))
    if len(_json(original).encode()) > 2 * 1024 * 1024:
        raise ValueError('The source exceeds the supported investment review size.')
    if existing:
        current = InvestmentImportDocument.objects.select_for_update().get(pk=existing.pk, user=user)
        if current.extracted_payload != existing.extracted_payload:
            raise InvestmentReviewConflict('The review changed during extraction. Reload it.')
        prior = (current.extracted_payload or {}).get('import_review', {})
        if prior.get('state') == 'pending' and prior.get('revision', 0):
            raise InvestmentReviewConflict('The edited draft is preserved. Review it before retrying.')
        document = current
    else:
        upload_file.seek(0)
        document = InvestmentImportDocument(user=user, uploaded_file=upload_file, file_name=upload_file.name)
    confidence = parsed.get('confidence', 0)
    confidence = confidence if type(confidence) in (int, float) and isfinite(confidence) else 0
    document.broker_name = str(parsed.get('broker') or '')[:120]
    document.parse_confidence = min(1, max(0, confidence))
    document.extracted_text = str(parsed.get('extracted_text') or '')[:20000]
    document.parser_status = 'needs_review' if rows or document.extracted_text else 'failed'
    document.summary = 'Extraction saved for review. No canonical investment records were changed.'
    payload = deepcopy(document.extracted_payload or {})
    previous = payload.get('import_review', {})
    if previous.get('state') == 'confirmed':
        receipts = payload.setdefault('import_review_receipts', [])
        if len(receipts) >= 100:
            raise InvestmentReviewConflict('Keep this source and upload a new copy to begin another review.')
        receipts.append({key: previous[key] for key in ('id', 'confirmed_at', 'confirmed_token', 'receipt')})
    candidates = []
    identities = set()
    for raw in original or [{}]:
        row = {field: raw.get(field) for field in FIELDS}
        row['field_status'] = {field: (raw.get('field_status') or {}).get(field,
            'missing' if row[field] in (None, '') else 'extracted') for field in FIELDS}
        matches = list(_matches(user, row).values_list('pk', flat=True))
        identity = _identity(row)
        duplicate = bool(identity) and identity in identities
        identities.add(identity)
        row.update(action='skip' if duplicate else 'link' if len(matches) == 1 else 'create',
                   target_id=matches[0] if len(matches) == 1 else None)
        candidates.append(row)
    payload.update(broker_name=document.broker_name, confidence=document.parse_confidence, investments=original)
    payload['import_review'] = dict(id=uuid4().hex, revision=0, state='pending', original=original,
        candidate=candidates, expires_at=(timezone.now()+timedelta(days=1)).isoformat())
    document.extracted_payload = payload
    document.save()
    source_status, fingerprint, _ = file_reference(document.uploaded_file)
    payload['source_sha256'] = fingerprint if source_status == 'available' else None
    document.save(update_fields=['extracted_payload'])
    operational_logging_service.log(user=user, module='investments', scope='investment_document',
        event_type='investment_preview_prepared', document_id=document.pk,
        message='Investment extraction saved for review; no financial posting.', payload={'row_count': len(rows)})
    return document


def _new_investment(row):
    data = {field: row.get(field) for field in FIELDS}
    errors = {}
    if isinstance(data['annual_return_rate'], bool):
        errors['annual_return_rate'] = 'Enter a finite return assumption.'
    for field in FIELDS:
        if field not in ('institution', 'account_number') and data[field] in (None, ''):
            errors[field] = 'Required from the source or explicit owner entry.'
        elif row['field_status'].get(field) == 'estimated':
            errors[field] = 'Check the original and explicitly save this unverified value.'
    if errors: return None, errors
    try:
        for field in MONEY: data[field] = investment_money(data[field])
    except ValueError:
        return None, {'amounts': 'Enter finite currency amounts within the supported range.'}
    data.update(institution=data['institution'] or '', account_number=data['account_number'] or '')
    serializer = InvestmentSerializer(data=data)
    return (serializer, {}) if serializer.is_valid() else (None, serializer.errors)


def investment_preview(document, *, page=1):
    review = _review(document)
    if type(page) is not int or page < 1:
        raise ValueError('Choose a valid page.')
    source_status, fingerprint, download = file_reference(document.uploaded_file)
    dependencies = []
    results = []
    identities = set()
    for index, row in enumerate(review['candidate']):
        matches = list(_matches(document.user, row).order_by('pk'))
        target = Investment.objects.filter(user=document.user, pk=row.get('target_id')).first() if type(row.get('target_id')) is int else None
        dependencies.append(dict(matches=[{field.attname: getattr(item, field.attname) for field in Investment._meta.concrete_fields}
                                          for item in matches], target=None if target is None else
                                {field.attname: getattr(target, field.attname) for field in Investment._meta.concrete_fields}))
        errors = {}
        if row['action'] == 'create':
            _, errors = _new_investment(row)
            if matches:
                errors['identity'] = 'Matching records exist. Select one to link without changing it, or skip this row.'
            identity = _identity(row)
            if identity and identity in identities:
                errors['identity'] = 'Duplicate investment identity in this source; link or skip the repeated row.'
            identities.add(identity)
        elif row['action'] == 'link':
            if target is None:
                errors['target_id'] = 'Select an owned existing investment.'
        elif row['action'] != 'skip':
            errors['action'] = 'Choose create, link or skip.'
        existing = None if target is None else {field: getattr(target, field) for field in FIELDS}
        conflicts = [] if existing is None else [field for field in FIELDS if row.get(field) is not None
            and str(row[field]) != str(existing[field])]
        if review['state'] == 'confirmed':
            errors = {}
        results.append(dict(row, index=index, original=review['original'][index] if index < len(review['original']) else {},
            errors=errors, existing=existing, conflicts=conflicts,
            matches=[{'id': item.pk, 'asset_name': item.asset_name, 'account': item.account_number} for item in matches]))
    binding = dict(owner=document.user_id, document=document.pk, review=review['id'], revision=review['revision'],
        candidate=_digest(review['candidate']), dependencies=_digest(dependencies), file=fingerprint,
        metadata=_digest(dict(kind=document.broker_name, text=document.extracted_text, source_name=document.uploaded_file.name,
                              linked=list(document.linked_investments.order_by('pk').values_list('pk', flat=True)))))
    expired = timezone.now() >= timezone.datetime.fromisoformat(review['expires_at'])
    source_ok = source_status == 'available' and fingerprint == (document.extracted_payload or {}).get('source_sha256')
    return dict(document_id=document.pk, state=review['state'], revision=review['revision'],
        token=signing.dumps(binding, salt=SALT) if review['state'] == 'pending' and not expired else None,
        expires_at=review['expires_at'], expired=expired, source_status=source_status, source_ok=source_ok,
        source_download=download, duplicate_documents=list(InvestmentImportDocument.objects.filter(user=document.user,
            extracted_payload__source_sha256=fingerprint).exclude(pk=document.pk).values_list('pk', flat=True)) if fingerprint else [],
        can_confirm=source_ok and not expired and review['state'] == 'pending' and not any(row['errors'] for row in results),
        rows=results[(page-1)*PAGE_SIZE:page*PAGE_SIZE], row_count=len(results), page=page,
        pages=max(1, (len(results)+PAGE_SIZE-1)//PAGE_SIZE), binding=binding)


@transaction.atomic
def edit_investment_review(document, *, revision, edits):
    document = InvestmentImportDocument.objects.select_for_update().get(pk=document.pk, user=document.user)
    review = _review(document)
    if type(revision) is not int or revision != review['revision'] or review['state'] != 'pending':
        raise InvestmentReviewConflict('The investment review changed. Reload it before editing.')
    if not isinstance(edits, list) or len(edits) > PAGE_SIZE:
        raise ValueError('Edit at most one page at a time.')
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) - {'index', *FIELDS, 'action', 'target_id'}:
            raise ValueError('Choose supported investment corrections.')
        index = edit.get('index')
        if type(index) is not int or not 0 <= index < len(review['candidate']):
            raise ValueError('Choose a investment row in this source.')
        row = review['candidate'][index]
        for field, value in edit.items():
            if field == 'index': continue
            if field in (*MONEY, 'annual_return_rate') and value not in (None, ''):
                if isinstance(value, bool): raise ValueError('Enter finite numeric values.')
                if field in MONEY:
                    amount = investment_money(value)
                    if amount < 0: raise ValueError('Investment amounts cannot be negative.')
                    value = str(amount)
                else:
                    try: number = Decimal(str(value))
                    except InvalidOperation: raise ValueError('Enter finite numeric values.') from None
                    if not number.is_finite():
                        raise ValueError('Enter a finite return assumption.')
                    value = str(number)
            elif field == 'action' and value not in ('create', 'link', 'skip'):
                raise ValueError('Choose create, link or skip.')
            elif field == 'target_id':
                if value is not None and (type(value) is not int or not Investment.objects.filter(user=document.user, pk=value).exists()):
                    raise ValueError('Select an owned existing investment.')
            elif value is not None and (not isinstance(value, str) or len(value) > 120):
                raise ValueError('Enter bounded investment fields.')
            row[field] = value if value != '' else None
            if field in FIELDS:
                row['field_status'][field] = 'owner_entered' if value not in (None, '') else 'missing'
    review['revision'] += 1
    document.parser_status = 'needs_review'
    document.save(update_fields=['extracted_payload', 'parser_status', 'updated_at'])
    return document


@transaction.atomic
def confirm_investment_review(document, *, token):
    document = InvestmentImportDocument.objects.select_for_update().get(pk=document.pk, user=document.user)
    review = _review(document)
    if not isinstance(token, str) or len(token) > 2048:
        raise ValueError('Explicitly confirm the current review.')
    if review['state'] == 'confirmed':
        if sha256(token.encode()).hexdigest() != review.get('confirmed_token'):
            raise InvestmentReviewConflict('This review was already confirmed.')
        return dict(review['receipt'], replayed=True)
    try: binding = signing.loads(token, salt=SALT, max_age=1800)
    except signing.BadSignature:
        raise InvestmentReviewConflict('The confirmation expired or changed. Reopen the review.') from None
    preview = investment_preview(document)
    if binding != preview['binding'] or not preview['can_confirm']:
        raise InvestmentReviewConflict('The source, investment or review changed. Review the current values.')
    payload = deepcopy(document.extracted_payload)
    payload['import_review']['state'] = 'confirming'
    if not InvestmentImportDocument.objects.filter(pk=document.pk, extracted_payload=document.extracted_payload).update(extracted_payload=payload):
        raise InvestmentReviewConflict('Another request changed this review.')
    linked, created = [], []
    for row in review['candidate']:
        if row['action'] == 'skip': continue
        if row['action'] == 'link':
            linked.append(Investment.objects.get(pk=row['target_id'], user=document.user))
        else:
            serializer, errors = _new_investment(row)
            if errors: raise InvestmentReviewConflict('The reviewed investment fields are no longer valid.')
            investment = serializer.save(user=document.user)
            linked.append(investment); created.append(investment)
    document.linked_investments.add(*linked)
    capture_import(document, linked, extraction=review['original'])
    receipt = dict(document_id=document.pk, created_count=len(created), linked_count=len(linked), replayed=False)
    payload['import_review'].update(state='confirmed', confirmed_at=timezone.now().isoformat(),
        confirmed_token=sha256(token.encode()).hexdigest(), receipt=receipt)
    document.extracted_payload = payload
    document.parser_status = 'parsed' if linked else 'needs_review'
    document.summary = 'Owner review confirmed; existing holdings were preserved.'
    document.save(update_fields=['extracted_payload', 'parser_status', 'summary', 'updated_at'])
    operational_logging_service.log(user=document.user, module='investments', scope='investment_document',
        event_type='investment_review_confirmed', document_id=document.pk,
        message='Reviewed investment document confirmed.', payload=receipt)
    return receipt
