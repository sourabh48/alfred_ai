"""Owned structured statement evidence; no OCR, model output or financial writes."""
from hashlib import sha256
from collections import Counter, defaultdict
import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from alfred_ai.services.upload_limits import read_upload_bytes
from ..models import Expense, StatementUpload, StatementTransactionEvidence
from ..money import expense_money


class EvidenceConflict(ValueError):
    pass


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _values(row):
    if row.amount is None: raise ValueError('Canonical transaction amount is missing.')
    return dict(transaction_date=row.transaction_date.isoformat(), direction=row.direction,
        amount=format(expense_money(row.amount), '.2f'),
        closing_balance=None if row.closing_balance is None else format(expense_money(row.closing_balance), '.2f'),
        category=row.category, classification=row.classification, bank_account_id=row.bank_account_id)


def capture_import(rows):
    # Import-only: retries/edits never replace original structured extraction evidence.
    StatementTransactionEvidence.objects.bulk_create([
        StatementTransactionEvidence(expense=row, statement_upload=row.statement_upload,
            source_values={**_values(row), 'transaction_fingerprint':row.transaction_fingerprint,
                           'document_name':document_name(row.statement_upload),
                           'statement_start':row.statement_upload.statement_start.isoformat() if row.statement_upload.statement_start else None,
                           'statement_end':row.statement_upload.statement_end.isoformat() if row.statement_upload.statement_end else None,
                           'parser_identity':row.transaction_identity}) for row in rows
    ])


def document_name(upload):
    name = str(upload.file_name or '').replace('\\', '/').rsplit('/', 1)[-1]
    return name[:160] if name and not any(ord(char) < 32 for char in name) else f'Bank statement #{upload.pk}'


def file_reference(source_file):
    if not source_file:
        return 'source_removed', None, None
    try:
        root = Path(settings.MEDIA_ROOT).resolve()
        target = Path(source_file.path).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            return 'source_unavailable', None, None
        with target.open('rb') as stream:
            fingerprint = sha256(read_upload_bytes(stream)).hexdigest()
        return 'available', fingerprint, reverse('private_media', kwargs={'path':target.relative_to(root).as_posix()})
    except (OSError, ValueError, SuspiciousFileOperation, NotImplementedError):
        return 'source_unavailable', None, None


def _owned(user, identity, document_id=None):
    rows = Expense.objects.select_related('bank_account', 'statement_upload__bank_account').filter(
        user=user, source='bank_statement', statement_upload__user=user)
    if document_id is not None: rows = rows.filter(statement_upload_id=document_id)
    row = get_object_or_404(rows, pk=identity)
    return _owned_row(user, row)


def _owned_row(user, row):
    from django.http import Http404
    if row.user_id != user.pk or row.source != 'bank_statement' or not row.statement_upload_id or row.statement_upload.user_id != user.pk:
        raise Http404
    upload = row.statement_upload
    if ((row.bank_account is not None and row.bank_account.user_id != user.pk)
            or (upload.bank_account is not None and upload.bank_account.user_id != user.pk)):
        raise Http404
    return row


def _reference_key(row):
    return row.bank_account_id, row.transaction_date, row.direction, row.external_reference, row.raw_description


def _state(row, proof, *, file_references=None, record_index=None):
    upload = row.statement_upload
    current = _values(row)
    if file_references is None:
        status, fingerprint, download = file_reference(upload.original_file)
    else:
        # One calculation may validate many rows from the same retained file.
        key = upload.original_file.name
        if key not in file_references:
            file_references[key] = file_reference(upload.original_file)
        status, fingerprint, download = file_references[key]
    payload = upload.extracted_payload if isinstance(upload.extracted_payload, dict) else {}
    metadata = dict(document_id=upload.pk, document_name=document_name(upload),
        statement_start=upload.statement_start.isoformat() if upload.statement_start else None,
        statement_end=upload.statement_end.isoformat() if upload.statement_end else None)
    base = _digest(dict(current=current, metadata=metadata, file=fingerprint, file_name=upload.original_file.name,
        source=upload.source, parser_status=upload.parser_status, user_id=row.user_id, statement_user_id=upload.user_id,
        account_number=upload.account_number, account_id=upload.bank_account_id, record_fingerprint=row.transaction_fingerprint,
        record_identity=row.transaction_identity, original=proof.source_values if proof and proof.source_values else None,
        description=row.description, raw_description=row.raw_description, merchant=row.merchant,
        external_reference=row.external_reference, partial=bool(payload.get('preview_only') or
            (payload.get('ocr_progress') or {}).get('is_partial'))))
    if status == 'available':
        normalize = lambda value: ''.join(char.casefold() for char in value if char.isalnum())
        if (row.bank_account_id is None or upload.bank_account_id is None or row.bank_account_id != upload.bank_account_id or
                (row.bank_account and upload.account_number and normalize(row.bank_account.account_number) != normalize(upload.account_number)) or
                (proof and proof.statement_upload_id != upload.pk) or
                (upload.statement_start and upload.statement_end and upload.statement_start > upload.statement_end) or
                (upload.statement_start and row.transaction_date < upload.statement_start) or
                (upload.statement_end and row.transaction_date > upload.statement_end)):
            status = 'conflicting_source'
        elif upload.source not in ('bank_statement', 'credit_card_statement') or upload.parser_status != 'parsed' or payload.get('preview_only') or (payload.get('ocr_progress') or {}).get('is_partial'):
            status = 'document_needs_review'
        elif row.external_reference and (len(record_index[0][_reference_key(row)]) > 1 if record_index is not None else Expense.objects.filter(user_id=row.user_id, bank_account_id=row.bank_account_id,
                transaction_date=row.transaction_date, direction=row.direction, external_reference=row.external_reference,
                raw_description=row.raw_description).exclude(pk=row.pk).exclude(amount=row.amount).exists()):
            status = 'conflicting_records'
        elif row.transaction_fingerprint and (record_index[1][(row.bank_account_id, row.transaction_fingerprint)] > 1 if record_index is not None else Expense.objects.filter(user_id=row.user_id, bank_account_id=row.bank_account_id,
                transaction_fingerprint=row.transaction_fingerprint).exclude(pk=row.pk).exists()):
            status = 'duplicate_records'
        else:
            status = 'owner_confirmed' if proof and proof.reviewed_at and proof.reviewed_revision == base else 'needs_owner_review'
    revision = _digest([base, proof.review_generation if proof else 0])
    public = dict(transaction_id=row.pk, statement=metadata, current=current,
        original=proof.source_values if proof and proof.source_values else None,
        original_status='retained_import_snapshot' if proof and proof.source_values else 'not_retained',
        verification=status, verified_at=proof.reviewed_at.isoformat() if status == 'owner_confirmed' else None,
        revision=revision, review_allowed=status in ('owner_confirmed', 'needs_owner_review'),
        citation_url=reverse('statement_evidence', kwargs={'document_id':upload.pk, 'transaction_id':row.pk}),
        source_download_url=download,
        limitations=['Owner confirmation is not independent bank authentication.', 'Currency was not recorded; no currency or aggregate is inferred.'])
    return public, base


def evidence(user, identity, *, document_id=None):
    row = _owned(user, identity, document_id)
    proof = StatementTransactionEvidence.objects.filter(expense=row).first()
    return _state(row, proof)[0]


def evidence_for_rows(user, rows):
    """Validate a complete owned row snapshot without per-transaction SQL or file reads."""
    from django.http import Http404
    if not any(row.source == 'bank_statement' for row in rows):
        return []
    references, fingerprints = defaultdict(set), Counter()
    for row in rows:
        if row.user_id == user.pk:
            references[_reference_key(row)].add(row.amount)
            fingerprints[(row.bank_account_id, row.transaction_fingerprint)] += 1
    proofs = {proof.expense_id: proof for proof in StatementTransactionEvidence.objects.filter(expense__user=user)}
    files, result = {}, []
    for row in rows:
        if row.source != 'bank_statement':
            continue
        try:
            _owned_row(user, row)
            detail = _state(row, proofs.get(row.pk), file_references=files, record_index=(references, fingerprints))[0]
            result.append((row.pk, detail['revision'], detail['verification']))
        except Http404:
            result.append((row.pk, None, 'source_unavailable'))
    return result


def review(user, identity, *, revision, confirm, revoke=False):
    if confirm is not True or not isinstance(revision, str) or len(revision) != 64:
        raise ValueError('Review the current source and confirm the displayed values.')
    with transaction.atomic():
        row = _owned(user, identity)
        # Lock the shared parent before the receipt to serialize owner reviews without changing money.
        StatementUpload.objects.select_for_update().get(pk=row.statement_upload_id, user=user)
        row = _owned(user, identity)
        proof = StatementTransactionEvidence.objects.select_for_update().filter(expense=row).first()
        current, base = _state(row, proof)
        if current['revision'] != revision or (not revoke and not current['review_allowed']):
            raise EvidenceConflict()
        if proof is None:
            proof = StatementTransactionEvidence(expense=row, statement_upload=row.statement_upload)
        proof.reviewed_revision = '' if revoke else base
        proof.reviewed_at = None if revoke else timezone.now()
        proof.review_generation += 1
        proof.save()
        return evidence(user, identity)


def choices(user):
    return [dict(id=row.pk, document_id=row.statement_upload_id,
        label=f'{document_name(row.statement_upload)} · {row.transaction_date.isoformat()} · record #{row.pk}')
        for row in Expense.objects.filter(user=user, source='bank_statement', statement_upload__user=user,
            bank_account__user=user, statement_upload__bank_account__user=user).select_related('statement_upload')
            .order_by('-transaction_date', '-pk')[:20]]
