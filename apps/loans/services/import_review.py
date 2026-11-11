"""Owned loan-document drafts; extraction cannot post or overwrite canonical loans."""
from copy import deepcopy
from datetime import date, timedelta
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
from ..models import Loan, LoanImportDocument
from ..money import loan_money
from ..serializers import LoanSerializer
from .document_evidence import capture_import

FIELDS = ('lender', 'loan_type', 'loan_account_number', 'principal', 'remaining_balance',
          'interest_rate', 'emi', 'tenure_months', 'start_date', 'currency')
MONEY = ('principal', 'remaining_balance', 'emi')
PAGE_SIZE = 10
SALT = 'alfred.loan-document-review.v1'
CLOSURE_TYPES = ('foreclosure_statement', 'closure_letter', 'noc')


class LoanReviewConflict(ValueError):
    pass


def _json(value):
    return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return sha256(_json(value).encode()).hexdigest()


def _review(document):
    review = (document.extracted_payload or {}).get('import_review')
    if not isinstance(review, dict) or review.get('state') not in ('pending', 'confirmed'):
        raise LoanReviewConflict('Retry the original source to prepare a review.')
    return review


def _matches(user, row):
    account = str(row.get('loan_account_number') or '').strip()
    if account:
        return Loan.objects.filter(user=user, loan_account_number__iexact=account)
    try:
        principal = loan_money(row.get('principal'))
    except ValueError:
        return Loan.objects.none()
    lender = str(row.get('lender') or '').strip()
    return Loan.objects.filter(user=user, lender__iexact=lender, principal=principal) if lender and principal else Loan.objects.none()


@transaction.atomic
def stage_loan_document(*, user, parsed, upload_file=None, existing=None):
    rows = parsed.get('loans') or []
    if not isinstance(rows, list) or len(rows) > 100 or any(not isinstance(row, dict) for row in rows):
        raise ValueError('The source exceeds the supported loan review size.')
    original = json.loads(_json(rows))
    if len(_json(original).encode()) > 2 * 1024 * 1024:
        raise ValueError('The source exceeds the supported loan review size.')
    if existing:
        current = LoanImportDocument.objects.select_for_update().get(pk=existing.pk, user=user)
        if current.extracted_payload != existing.extracted_payload:
            raise LoanReviewConflict('The review changed during extraction. Reload it.')
        prior = (current.extracted_payload or {}).get('import_review', {})
        if prior.get('state') == 'pending' and prior.get('revision', 0):
            raise LoanReviewConflict('The edited draft is preserved. Review it before retrying.')
        document = current
    else:
        upload_file.seek(0)
        document = LoanImportDocument(user=user, uploaded_file=upload_file, file_name=upload_file.name)
    confidence = parsed.get('confidence', 0)
    confidence = confidence if type(confidence) in (int, float) and isfinite(confidence) else 0
    document.document_type = str(parsed.get('document_type') or 'other')[:40]
    document.parse_confidence = min(1, max(0, confidence))
    document.extracted_text = str(parsed.get('extracted_text') or '')[:20000]
    document.parser_status = 'needs_review' if rows or document.extracted_text else 'failed'
    document.summary = 'Extraction saved for review. No canonical loan records were changed.'
    payload = deepcopy(document.extracted_payload or {})
    previous = payload.get('import_review', {})
    if previous.get('state') == 'confirmed':
        receipts = payload.setdefault('import_review_receipts', [])
        if len(receipts) >= 100:
            raise LoanReviewConflict('Keep this source and upload a new copy to begin another review.')
        receipts.append({key: previous[key] for key in ('id', 'confirmed_at', 'confirmed_token', 'receipt')})
    candidates = []
    identities = set()
    for raw in original or [{}]:
        row = {field: raw.get(field) for field in FIELDS}
        row['field_status'] = {field: (raw.get('field_status') or {}).get(field,
            'missing' if row[field] in (None, '', 'Unknown Lender') else 'extracted') for field in FIELDS}
        matches = list(_matches(user, row).values_list('pk', flat=True))
        identity = str(row['loan_account_number'] or '').strip().casefold()
        duplicate = bool(identity) and identity in identities
        identities.add(identity)
        row.update(action='skip' if duplicate else 'link' if len(matches) == 1 else 'create',
                   target_id=matches[0] if len(matches) == 1 else None)
        candidates.append(row)
    payload.update(document_type=document.document_type, confidence=document.parse_confidence, loans=original)
    payload['import_review'] = dict(id=uuid4().hex, revision=0, state='pending', original=original,
        candidate=candidates, expires_at=(timezone.now()+timedelta(days=1)).isoformat())
    document.extracted_payload = payload
    document.save()
    source_status, fingerprint, _ = file_reference(document.uploaded_file)
    payload['source_sha256'] = fingerprint if source_status == 'available' else None
    document.save(update_fields=['extracted_payload'])
    operational_logging_service.log(user=user, module='loans', scope='loan_document',
        event_type='loan_preview_prepared', document_id=document.pk,
        message='Loan extraction saved for review; no financial posting.', payload={'row_count': len(rows)})
    return document


def _new_loan(row):
    errors = {}
    data = {field: row.get(field) for field in FIELDS}
    for field in FIELDS:
        if data[field] in (None, '', 'Unknown Lender'):
            errors[field] = 'Required from the source or explicit owner entry.'
        elif (row.get('field_status') or {}).get(field) == 'estimated':
            errors[field] = 'Review and explicitly enter this estimated value.'
    for field in (*MONEY, 'interest_rate', 'tenure_months'):
        if isinstance(data[field], bool): errors[field] = 'Enter a finite number.'
    if errors:
        return None, errors
    try:
        for field in MONEY:
            data[field] = loan_money(data[field])
        if data['remaining_balance'] <= 0:
            return None, {'remaining_balance': 'Use the separate closure workflow; this import cannot close a loan.'}
    except ValueError:
        return None, {'amounts': 'Enter finite amounts within the supported range.'}
    serializer = LoanSerializer(data=data)
    return (serializer, {}) if serializer.is_valid() else (None, serializer.errors)


def loan_preview(document, *, page=1):
    review = _review(document)
    if type(page) is not int or page < 1:
        raise ValueError('Choose a valid page.')
    source_status, fingerprint, download = file_reference(document.uploaded_file)
    dependencies = []
    results = []
    identities = set()
    for index, row in enumerate(review['candidate']):
        matches = list(_matches(document.user, row).order_by('pk'))
        target = Loan.objects.filter(user=document.user, pk=row.get('target_id')).first() if type(row.get('target_id')) is int else None
        dependencies.append(dict(matches=[{field.attname: getattr(item, field.attname) for field in Loan._meta.concrete_fields}
                                          for item in matches], target=None if target is None else
                                {field.attname: getattr(target, field.attname) for field in Loan._meta.concrete_fields}))
        errors = {}
        if row['action'] == 'create':
            _, errors = _new_loan(row)
            if matches:
                errors['identity'] = 'Matching records exist. Select one to link without changing it, or skip this row.'
            identity = str(row.get('loan_account_number') or '').strip().casefold()
            if identity and identity in identities:
                errors['identity'] = 'Duplicate loan identity in this source; link or skip the repeated row.'
            identities.add(identity)
            if document.document_type in CLOSURE_TYPES:
                errors['document_type'] = 'Closure evidence may be linked, but cannot create or close loans here.'
        elif row['action'] == 'link':
            if target is None:
                errors['target_id'] = 'Select an owned existing loan.'
        elif row['action'] != 'skip':
            errors['action'] = 'Choose create, link or skip.'
        existing = None if target is None else {field: getattr(target, field) for field in FIELDS}
        conflicts = [] if existing is None else [field for field in FIELDS if row.get(field) is not None
            and str(row[field]) != str(existing[field])]
        if review['state'] == 'confirmed':
            errors = {}
        results.append(dict(row, index=index, original=review['original'][index] if index < len(review['original']) else {},
            errors=errors, existing=existing, conflicts=conflicts,
            matches=[{'id': item.pk, 'lender': item.lender, 'account': item.loan_account_number} for item in matches]))
    binding = dict(owner=document.user_id, document=document.pk, review=review['id'], revision=review['revision'],
        candidate=_digest(review['candidate']), dependencies=_digest(dependencies), file=fingerprint,
        metadata=_digest(dict(kind=document.document_type, text=document.extracted_text, source_name=document.uploaded_file.name,
                              linked=list(document.linked_loans.order_by('pk').values_list('pk', flat=True)))))
    expired = timezone.now() >= timezone.datetime.fromisoformat(review['expires_at'])
    source_ok = source_status == 'available' and fingerprint == (document.extracted_payload or {}).get('source_sha256')
    return dict(document_id=document.pk, state=review['state'], revision=review['revision'],
        token=signing.dumps(binding, salt=SALT) if review['state'] == 'pending' and not expired else None,
        expires_at=review['expires_at'], expired=expired, source_status=source_status, source_ok=source_ok,
        source_download=download, duplicate_documents=list(LoanImportDocument.objects.filter(user=document.user,
            extracted_payload__source_sha256=fingerprint).exclude(pk=document.pk).values_list('pk', flat=True)) if fingerprint else [],
        can_confirm=source_ok and not expired and review['state'] == 'pending' and not any(row['errors'] for row in results),
        rows=results[(page-1)*PAGE_SIZE:page*PAGE_SIZE], row_count=len(results), page=page,
        pages=max(1, (len(results)+PAGE_SIZE-1)//PAGE_SIZE), binding=binding)


@transaction.atomic
def edit_loan_review(document, *, revision, edits):
    document = LoanImportDocument.objects.select_for_update().get(pk=document.pk, user=document.user)
    review = _review(document)
    if type(revision) is not int or revision != review['revision'] or review['state'] != 'pending':
        raise LoanReviewConflict('The loan review changed. Reload it before editing.')
    if not isinstance(edits, list) or len(edits) > PAGE_SIZE:
        raise ValueError('Edit at most one page at a time.')
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) - {'index', *FIELDS, 'action', 'target_id'}:
            raise ValueError('Choose supported loan corrections.')
        index = edit.get('index')
        if type(index) is not int or not 0 <= index < len(review['candidate']):
            raise ValueError('Choose a loan row in this source.')
        row = review['candidate'][index]
        for field, value in edit.items():
            if field == 'index': continue
            if field in (*MONEY, 'interest_rate', 'tenure_months') and value not in (None, ''):
                if isinstance(value, bool): raise ValueError('Enter finite numeric values.')
                if field in MONEY:
                    amount = loan_money(value)
                    if amount < 0: raise ValueError('Loan amounts cannot be negative.')
                    value = str(amount)
                else:
                    try: number = Decimal(str(value))
                    except InvalidOperation: raise ValueError('Enter finite numeric values.') from None
                    if not number.is_finite() or number < 0 or (field == 'tenure_months' and number != number.to_integral_value()):
                        raise ValueError('Enter valid rates and whole-month tenure.')
                    value = int(number) if field == 'tenure_months' else str(number)
            elif field == 'start_date' and value:
                value = date.fromisoformat(value).isoformat()
            elif field == 'action' and value not in ('create', 'link', 'skip'):
                raise ValueError('Choose create, link or skip.')
            elif field == 'target_id':
                if value is not None and (type(value) is not int or not Loan.objects.filter(user=document.user, pk=value).exists()):
                    raise ValueError('Select an owned existing loan.')
            elif value is not None and (not isinstance(value, str) or len(value) > 120):
                raise ValueError('Enter bounded loan fields.')
            row[field] = value if value != '' else None
            if field in FIELDS:
                row['field_status'][field] = 'owner_entered' if value not in (None, '') else 'missing'
    review['revision'] += 1
    document.save(update_fields=['extracted_payload'])
    return document


@transaction.atomic
def confirm_loan_review(document, *, token):
    document = LoanImportDocument.objects.select_for_update().get(pk=document.pk, user=document.user)
    review = _review(document)
    if not isinstance(token, str) or len(token) > 2048:
        raise ValueError('Explicitly confirm the current review.')
    if review['state'] == 'confirmed':
        if sha256(token.encode()).hexdigest() != review.get('confirmed_token'):
            raise LoanReviewConflict('This review was already confirmed.')
        return dict(review['receipt'], replayed=True)
    try: binding = signing.loads(token, salt=SALT, max_age=1800)
    except signing.BadSignature:
        raise LoanReviewConflict('The confirmation expired or changed. Reopen the review.') from None
    preview = loan_preview(document)
    if binding != preview['binding'] or not preview['can_confirm']:
        raise LoanReviewConflict('The source, loan or review changed. Review the current values.')
    payload = deepcopy(document.extracted_payload)
    payload['import_review']['state'] = 'confirming'
    if not LoanImportDocument.objects.filter(pk=document.pk, extracted_payload=document.extracted_payload).update(extracted_payload=payload):
        raise LoanReviewConflict('Another request changed this review.')
    linked, created, originals = [], [], {}
    for index, row in enumerate(review['candidate']):
        if row['action'] == 'skip': continue
        if row['action'] == 'link':
            linked.append(Loan.objects.get(pk=row['target_id'], user=document.user))
        else:
            serializer, errors = _new_loan(row)
            if errors: raise LoanReviewConflict('The reviewed loan fields are no longer valid.')
            loan = serializer.save(user=document.user)
            linked.append(loan); created.append(loan)
        # Edited identities cannot identify the immutable source row; repeated links remain ambiguous.
        originals[linked[-1].pk] = {} if linked[-1].pk in originals else review['original'][index]
    document.linked_loans.add(*linked)
    capture_import(document, linked, originals=originals)
    receipt = dict(document_id=document.pk, created_count=len(created), linked_count=len(linked), replayed=False)
    payload['import_review'].update(state='confirmed', confirmed_at=timezone.now().isoformat(),
        confirmed_token=sha256(token.encode()).hexdigest(), receipt=receipt)
    document.extracted_payload = payload
    document.parser_status = 'parsed' if linked else 'needs_review'
    document.summary = 'Owner review confirmed; existing loan balances and closure state were preserved.'
    document.save(update_fields=['extracted_payload', 'parser_status', 'summary'])
    operational_logging_service.log(user=document.user, module='loans', scope='loan_document',
        event_type='loan_review_confirmed', document_id=document.pk,
        message='Reviewed loan document confirmed.', payload=receipt)
    return receipt
