"""Owner attestation of imported fields, separate from loan/closure verification."""
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.expenses.services.statement_evidence import file_reference, document_name, EvidenceConflict
from apps.ml_engine.services.canonical_evidence import _digest
from ..models import LoanImportDocument, LoanDocumentEvidence
from ..money import loan_money

FIELDS = ('principal', 'emi', 'remaining_balance')


@transaction.atomic
def capture_import(document, rows, *, extraction=None):
    """Keep the first unambiguous parser output; never infer legacy originals."""
    for row in rows:
        if row.user_id != document.user_id:
            raise ValueError('Loan evidence ownership mismatch.')
        values = {}
        if extraction is not None:
            candidates = [item for item in extraction if isinstance(item, dict) and (
                str(item.get('loan_account_number') or '').strip() == row.loan_account_number if row.loan_account_number else
                not item.get('loan_account_number') and (item.get('lender') or '').strip() == row.lender
                and (item.get('loan_type') or 'other') == row.loan_type)]
            if len(candidates) == 1:
                for field in FIELDS:
                    value = candidates[0].get(field)
                    if value is None or isinstance(value, (bool, list, dict)) or len(str(value)) > 80:
                        continue
                    try: loan_money(value)
                    except ValueError: continue
                    values[field] = str(value)
        LoanDocumentEvidence.objects.get_or_create(document=document, original_loan_id=row.pk,
            defaults={'loan':row, 'source_values':values})


def _owned(user, document_id, identity):
    document = get_object_or_404(LoanImportDocument, user=user, pk=document_id)
    if document.linked_loans.exclude(user=user).exists(): raise Http404
    row = get_object_or_404(document.linked_loans.filter(user=user), pk=identity)
    return document, row


def _state(document, row, proof):
    status, fingerprint, download = file_reference(document.uploaded_file)
    payload = document.extracted_payload if isinstance(document.extracted_payload, dict) else {}
    current = {field:None if getattr(row,field) is None else format(loan_money(getattr(row,field)),'.2f') for field in FIELDS}
    original = proof.source_values if proof else {}
    base = _digest(dict(record={field.attname:getattr(row,field.attname) for field in row._meta.concrete_fields},
        document_id=document.pk, document_owner=document.user_id, parser_status=document.parser_status,
        payload=payload, original=original, file=fingerprint, file_name=document.uploaded_file.name, name=document.file_name))
    allowed = (status == 'available' and document.parser_status == 'parsed'
        and not payload.get('preview_only') and not (payload.get('ocr_progress') or {}).get('is_partial'))
    fields = {}
    for field in FIELDS:
        receipt = (proof.reviewed_fields.get(field) or {}) if proof else {}
        verified = allowed and current[field] is not None and receipt.get('revision') == base
        fields[field] = dict(current=current[field], original=original.get(field),
            original_status='retained_parser_value' if field in original else 'not_retained',
            verification='not_recorded' if current[field] is None else 'owner_confirmed' if verified else 'needs_owner_review' if allowed else 'source_unavailable',
            confirmed_at=receipt.get('at') if verified else None,
            currency=None, currency_status='not_recorded', provenance=f'loans.Loan.{field}')
    detail = dict(document_id=document.pk, loan_id=row.pk, document_name=document_name(document),
        fields=fields, revision=_digest([base, proof.review_generation if proof else 0]),
        source_status=status, source_fingerprint=fingerprint, review_allowed=allowed, source_download_url=download,
        applicable_date=row.updated_at.isoformat(),
        citation_url=reverse('loan_import_evidence',kwargs={'document_id':document.pk,'identity':row.pk}),
        limitations=['Owner confirmation is not bank authentication, loan-contract confirmation or closure verification.',
            'Parser output may include estimated/defaulted values. Check each current value against the document.',
            'Current corrected register values take precedence; original parser output is never rewritten.',
            'Currency was not recorded. No currency or compatible total is inferred.'])
    return detail, base


def evidence(user, document_id, identity):
    document, row = _owned(user, document_id, identity)
    proof = LoanDocumentEvidence.objects.filter(document=document, loan=row).first()
    return _state(document, row, proof)[0]


def review(user, document_id, identity, *, revision, fields, confirm, revoke=False):
    if (confirm is not True or not isinstance(revision,str) or len(revision)!=64 or not isinstance(fields,list)
            or not fields or any(not isinstance(field,str) or field not in FIELDS for field in fields)
            or len(set(fields)) != len(fields)):
        raise ValueError('Select current fields and explicitly confirm the source review.')
    with transaction.atomic():
        document, row = _owned(user, document_id, identity)
        LoanImportDocument.objects.select_for_update().get(pk=document.pk, user=user)
        document, row = _owned(user, document_id, identity)
        proof = LoanDocumentEvidence.objects.select_for_update().filter(document=document, loan=row).first()
        detail, base = _state(document,row,proof)
        if revision != detail['revision'] or (not revoke and not detail['review_allowed']): raise EvidenceConflict()
        if not revoke and any(detail['fields'][field]['current'] is None for field in fields):
            raise ValueError('Missing recorded values cannot be confirmed.')
        if proof is None:
            capture_import(document,[row])
            proof = LoanDocumentEvidence.objects.get(document=document,loan=row)
        confirmed = dict(proof.reviewed_fields)
        for field in fields:
            if revoke: confirmed.pop(field,None)
            else: confirmed[field] = dict(revision=base, at=timezone.now().isoformat())
        updated = LoanDocumentEvidence.objects.filter(pk=proof.pk,review_generation=proof.review_generation).update(
            reviewed_fields=confirmed,review_generation=F('review_generation')+1)
        if updated!=1: raise EvidenceConflict()
        return evidence(user,document_id,identity)
