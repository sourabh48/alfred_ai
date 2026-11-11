"""Persisted statement previews; only reviewed, current owner confirmations post money."""
from dataclasses import asdict
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import uuid4

from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from ..models import BankAccount, Expense, StatementUpload
from ..money import expense_money, identity_amount
from .statement_import import ParsedTransaction, StatementParseResult, clean_statement_text
from .transaction_intelligence import _normalize_account_number, build_transaction_fingerprint, build_reference_signature
from .statement_evidence import file_reference

SALT = 'alfred.statement-review.v1'
MAX_ROWS = 2000
PAGE_SIZE = 100


class StatementReviewConflict(ValueError):
    pass


def _json(value):
    return json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return sha256(_json(value).encode()).hexdigest()


def _parsed(snapshot):
    data = dict(snapshot)
    data['transactions'] = [ParsedTransaction(**{
        **item, 'transaction_date': date.fromisoformat(item['transaction_date']),
        'amount': Decimal(str(item['amount'])),
        'closing_balance': None if item['closing_balance'] is None else Decimal(str(item['closing_balance'])),
    }) for item in data['transactions']]
    for field in ('statement_start', 'statement_end'):
        data[field] = date.fromisoformat(data[field]) if data[field] else None
    return StatementParseResult(**data)


@transaction.atomic
def stage_statement(*, user, parsed, statement_kind, statement_file=None, existing_upload=None):
    from .statement_lifecycle import _validate_transaction_money, _save_upload_metadata, StatementLifecycleResult
    _validate_transaction_money(parsed)
    if len(parsed.transactions) > MAX_ROWS:
        raise ValueError('This statement exceeds the supported review size.')
    for field in ('bank_name', 'account_holder', 'account_number'):
        setattr(parsed, field, clean_statement_text(getattr(parsed, field)))
    snapshot = json.loads(_json(asdict(parsed)))
    if len(_json(snapshot).encode()) > 8 * 1024 * 1024:
        raise ValueError('This statement exceeds the supported review size.')
    if existing_upload is not None:
        current = StatementUpload.objects.select_for_update().get(pk=existing_upload.pk, user=user)
        if current.extracted_payload != existing_upload.extracted_payload:
            raise StatementReviewConflict('The preview changed during parsing. Reload it before retrying.')
        review = (current.extracted_payload or {}).get('import_review', {})
        if review.get('state') == 'pending' and review.get('revision', 0):
            raise StatementReviewConflict('The edited preview is preserved. Finish reviewing it before retrying.')
        existing_upload = current
    upload = _save_upload_metadata(user=user, statement_file=statement_file, parsed=parsed,
        statement_kind=statement_kind, bank_account=existing_upload.bank_account if existing_upload else None,
        existing_upload=existing_upload)
    payload = dict(upload.extracted_payload)
    previous = payload.get('import_review', {})
    if previous.get('state') == 'confirmed':
        receipts = list(payload.get('import_review_receipts', []))
        if len(receipts) >= 100:
            raise StatementReviewConflict('This source has reached its retained review limit. Keep it and upload a new source.')
        receipts.append({key: previous[key] for key in ('id', 'confirmed_at', 'confirmed_token', 'receipt')})
        payload['import_review_receipts'] = receipts
    payload['import_review'] = dict(id=uuid4().hex, revision=0, state='pending',
        expires_at=(timezone.now() + timedelta(days=1)).isoformat(), original=snapshot, candidate=snapshot)
    payload['source_sha256'] = file_reference(upload.original_file)[1]
    upload.extracted_payload = payload
    upload.save(update_fields=['extracted_payload'])
    from apps.reports.services import operational_logging_service
    operational_logging_service.log(user=user, module='expenses', category='document', scope='statement_document',
        event_type='statement_preview_prepared', document_id=upload.pk,
        message='Extraction saved for owner review; no financial posting.',
        payload={'row_count': len(parsed.transactions), 'parser_status': parsed.parser_status})
    return StatementLifecycleResult(upload, upload.bank_account, [], [], 0,
        dict(detected_loans=0, updated_loans=0, new_payments=0, review_payments=0), 0, upload.imported_count)


def _review(upload):
    review = (upload.extracted_payload or {}).get('import_review')
    if not isinstance(review, dict) or review.get('state') not in ('pending', 'confirmed'):
        raise StatementReviewConflict('Retry this source to prepare a preview before confirming.')
    return review


def _dependencies(user, snapshot):
    account_number = _normalize_account_number(snapshot['account_number'])
    account = BankAccount.objects.filter(user=user, account_number=account_number).first() if account_number else None
    dates = [item['transaction_date'] for item in snapshot['transactions']]
    rows = [] if account is None else list(Expense.objects.filter(user=user, bank_account=account, source='bank_statement',
        transaction_date__in=dates).order_by('pk').values('pk', 'transaction_fingerprint', 'transaction_date',
        'amount', 'closing_balance', 'direction', 'external_reference', 'raw_description', 'transaction_identity'))
    account_data = None if account is None else {field: getattr(account, field) for field in (
        'pk', 'account_number', 'bank_name', 'account_holder', 'account_type', 'currency', 'current_balance', 'last_synced_at')}
    return account, rows, _digest(dict(account=account_data, transactions=rows))


def statement_preview(upload, *, page=1):
    review = _review(upload)
    if type(page) is not int or page < 1:
        raise ValueError('Choose a valid preview page.')
    snapshot = review['candidate']
    account, existing, dependency = _dependencies(upload.user, snapshot)
    virtual_account = account or SimpleNamespace(account_number=_normalize_account_number(snapshot['account_number']))
    fingerprints = {row['transaction_fingerprint'] for row in existing}
    signatures = {build_reference_signature(transaction_date=row['transaction_date'],
        amount=identity_amount(row['transaction_identity'], 'amount', row['amount']), direction=row['direction'],
        external_reference=row['external_reference'], raw_description=row['raw_description']) for row in existing}
    preview = []
    duplicates = 0
    for index, item in enumerate(_parsed(snapshot).transactions):
        fingerprint = build_transaction_fingerprint(bank_account=virtual_account, **{
            field: getattr(item, field) for field in ('transaction_date', 'amount', 'direction',
                                                     'external_reference', 'raw_description', 'closing_balance')})
        signature = build_reference_signature(**{field: getattr(item, field) for field in (
            'transaction_date', 'amount', 'direction', 'external_reference', 'raw_description')})
        duplicate = fingerprint in fingerprints or (bool(signature[3]) and signature in signatures)
        duplicates += int(duplicate)
        fingerprints.add(fingerprint); signatures.add(signature)
        preview.append(dict(index=index, duplicate=bool(duplicate), **snapshot['transactions'][index],
                            original=review['original']['transactions'][index]))
        preview[-1]['amount'] = str(expense_money(item.amount))
        preview[-1]['closing_balance'] = None if item.closing_balance is None else str(expense_money(item.closing_balance))
    source_status, fingerprint, _ = file_reference(upload.original_file)
    source_ok = source_status == 'available' and fingerprint == (upload.extracted_payload or {}).get('source_sha256')
    binding = dict(owner=upload.user_id, upload=upload.pk, review=review['id'], revision=review['revision'], source=fingerprint,
                   candidate=_digest(snapshot), dependencies=dependency, metadata=_digest({field: getattr(upload, field)
                       for field in ('source', 'bank_name', 'account_holder', 'account_number', 'statement_start', 'statement_end')}))
    expired = timezone.now() >= timezone.datetime.fromisoformat(review['expires_at'])
    return dict(upload_id=upload.pk, state=review['state'], revision=review['revision'],
        token=signing.dumps(binding, salt=SALT) if review['state'] == 'pending' and not expired else None,
        expired=expired, expires_at=review['expires_at'], token_max_age_seconds=1800, source_ok=source_ok,
        confidence=snapshot['confidence'], parser_notes=snapshot['parser_notes'], partial=bool(snapshot['preview_only']),
        account_number=snapshot['account_number'], bank_name=snapshot['bank_name'],
        existing_account=account_data_public(account), proposed_closing_balance=preview[-1]['closing_balance'] if preview else None,
        rows=preview[(page-1)*PAGE_SIZE:page*PAGE_SIZE], page=page,
        pages=max(1, (len(preview)+PAGE_SIZE-1)//PAGE_SIZE), row_count=len(preview), duplicate_count=duplicates,
        new_count=len(preview)-duplicates, can_confirm=bool(preview) and bool(_normalize_account_number(snapshot['account_number']))
            and source_ok and not expired and review['state'] == 'pending')


def account_data_public(account):
    return None if account is None else dict(id=account.pk, current_balance=account.current_balance, currency=account.currency)


@transaction.atomic
def edit_statement_preview(upload, *, revision, edits, account_number=None):
    upload = StatementUpload.objects.select_for_update().get(pk=upload.pk, user=upload.user)
    review = _review(upload)
    if review['state'] != 'pending' or type(revision) is not int or review['revision'] != revision:
        raise StatementReviewConflict('The preview changed. Reload it before editing.')
    if not isinstance(edits, list) or len(edits) > PAGE_SIZE:
        raise ValueError('Edit at most one preview page at a time.')
    snapshot = review['candidate']
    if account_number is not None:
        if not isinstance(account_number, str) or len(account_number) > 64 or not _normalize_account_number(account_number):
            raise ValueError('Enter the account number from the source.')
        snapshot['account_number'] = _normalize_account_number(account_number)
        upload.account_number = snapshot['account_number']
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) - {'index', 'amount', 'closing_balance', 'transaction_date', 'direction'}:
            raise ValueError('Choose supported row corrections.')
        index = edit.get('index')
        if type(index) is not int or not 0 <= index < len(snapshot['transactions']):
            raise ValueError('Choose a row in this preview.')
        row = snapshot['transactions'][index]
        for field, value in edit.items():
            if field in ('amount', 'closing_balance'):
                if field == 'closing_balance' and value is None:
                    row[field] = None
                else:
                    amount = expense_money(value)
                    if field == 'amount' and amount <= 0:
                        raise ValueError('Transaction amounts must be positive; choose debit or credit separately.')
                    row[field] = str(amount)
            elif field == 'transaction_date':
                row[field] = date.fromisoformat(value).isoformat()
            elif field == 'direction':
                if value not in ('debit', 'credit'):
                    raise ValueError('Choose debit or credit.')
                row[field] = value
    review['revision'] += 1
    retry = upload.extracted_payload.get('background_retry', {})
    if retry.get('state') in ('queued', 'running'):
        retry.update(state='superseded', resolution='owner_review_saved')
    upload.save(update_fields=['extracted_payload', 'account_number'])
    return upload


@transaction.atomic
def confirm_statement(upload, *, token):
    from .statement_lifecycle import _post_reviewed_statement_upload
    upload = StatementUpload.objects.select_for_update().get(pk=upload.pk, user=upload.user)
    review = _review(upload)
    if not isinstance(token, str) or len(token) > 2048:
        raise ValueError('Review the preview before confirming.')
    if review['state'] == 'confirmed':
        if review.get('confirmed_token') != sha256(token.encode()).hexdigest():
            raise StatementReviewConflict('This preview was already confirmed.')
        return dict(review['receipt'], replayed=True)
    try:
        binding = signing.loads(token, salt=SALT, max_age=1800)
    except signing.BadSignature:
        raise StatementReviewConflict('The confirmation expired or changed. Reload the preview.') from None
    preview = statement_preview(upload)
    expected = signing.loads(preview['token'], salt=SALT) if preview['token'] else None
    if binding != expected or not preview['can_confirm']:
        raise StatementReviewConflict('The source or account changed. Review the current preview before confirming.')
    # The conditional update also claims the single writer on SQLite, where row locks are unavailable.
    previous = _json(upload.extracted_payload)
    payload = json.loads(previous)
    payload['import_review']['state'] = 'confirming'
    if not StatementUpload.objects.filter(pk=upload.pk, extracted_payload=upload.extracted_payload).update(extracted_payload=payload):
        raise StatementReviewConflict('Another request changed this preview.')
    upload.extracted_payload = payload
    result = _post_reviewed_statement_upload(user=upload.user, parsed=_parsed(review['candidate']),
        statement_kind=upload.source, existing_upload=upload)
    receipt = dict(upload_id=upload.pk, imported_count=result.new_import_count, skipped_count=result.skipped_count,
                   account_id=result.bank_account.pk if result.bank_account else None, replayed=False)
    payload = result.upload.extracted_payload
    payload['import_review'].update(state='confirmed', confirmed_at=timezone.now().isoformat(),
        confirmed_token=sha256(token.encode()).hexdigest(), receipt=receipt)
    result.upload.extracted_payload = payload
    result.upload.save(update_fields=['extracted_payload'])
    return receipt
