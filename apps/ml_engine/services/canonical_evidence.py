"""Read-only individual financial records; unknown currencies never form new totals."""
from datetime import datetime
from hashlib import sha256
import json
import re

from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.expenses.models import Expense
from apps.expenses.money import expense_money
from apps.budgets.models import Budget
from apps.budgets.money import budget_money
from apps.loans.models import Loan
from apps.loans.money import loan_money
from apps.investments.models import Investment
from apps.investments.money import investment_money
from .persistent_memory import _owner

MODELS={'expense':Expense,'budget':Budget,'loan':Loan,'investment':Investment}
KINDS=(*MODELS,'baseline')
BASELINE_KEYS=('monthly_income','liquid_cash','recurring_emi_burden','total_assets','total_liabilities','net_worth')


def _digest(value):
    return sha256(json.dumps(value,sort_keys=True,allow_nan=False,default=str).encode()).hexdigest()


def _amount(value, helper, status, source):
    return dict(amount=None if value is None else format(helper(value),'.2f'),currency=None,
        currency_status='not_recorded',evidence_status='unavailable' if value is None else status,provenance=source)


def _month(value):
    for pattern in ('%b %Y','%B %Y','%Y-%m'):
        try: return datetime.strptime(value.strip(),pattern).date().replace(day=1).isoformat()
        except ValueError: pass
    return None


def baseline_source(user):
    from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
    from apps.users.money import profile_money
    _owner(user)
    owner=get_object_or_404(get_user_model(),pk=user.pk)
    baseline=resolve_canonical_financial_baseline(owner,fresh=True)
    data=dict(record_type='baseline',record_id=owner.pk,applicable_date=timezone.localdate().isoformat(),
        provenance='resolve_canonical_financial_baseline (fresh)',verification='user_recorded',
        limitations=['Legacy totals require approved matching currency evidence and are withheld.',
            'Reported income and housing are not independently verified.'],amounts={},metric_states={})
    for key in (*BASELINE_KEYS,'rent_burden'):
        state=baseline['metric_states'][key]
        supported=(key=='rent_burden' or (key=='monthly_income' and baseline['income_source']=='reported_monthly_income'
            and owner.monthly_income>0 and baseline['decimal_amounts']['monthly_income']==format(profile_money(owner.monthly_income),'.2f')))
        value=owner.rent_or_emi if key=='rent_burden' else baseline['decimal_amounts'].get(key)
        available=supported and state['status']!='unavailable'
        data['amounts'][key]=_amount(value if available else None,profile_money,state['status'],state['source'])
        data['amounts'][key]['limitation']=None if available else 'Unavailable or requires approved currency/source compatibility.'
        data['metric_states'][key]=dict(status=state['status'] if available else 'unavailable',source=state['source'])
        data[key]=float(value) if available else None
    return _source('baseline',owner.pk,data,dict(owner=owner.pk,data=data),available=any(
        value['amount'] is not None for value in data['amounts'].values()))


def _source(kind, identity, data, revision_data, *, available=True):
    revision=_digest(revision_data)
    for value in data['amounts'].values():
        value.update(record_type=kind,record_id=identity,as_of=data['applicable_date'],revision=revision)
    return dict(ref=f'canonical-{kind}-{identity}',classification='canonical_record',record_type=kind,record_id=identity,
        revision=revision,as_of=data['applicable_date'],verified_at=None,available=available,
        url=reverse('canonical_evidence',kwargs={'kind':kind,'identity':identity}),data=data)


def record_source(user, kind, identity):
    _owner(user)
    if kind not in KINDS or type(identity) is not int or identity<1: raise Http404
    if kind=='baseline':
        if identity!=user.pk: raise Http404
        return baseline_source(user)
    row=get_object_or_404(MODELS[kind],pk=identity,user=user)
    data=dict(record_type=kind,record_id=row.pk,verification='user_recorded',
        applicable_date=None,provenance=f'{row._meta.label} persisted fields',amounts={},
        limitations=['Canonical recorded values are not independent third-party authentication.',
            'Currency was not recorded; no totals, currency conversion or live valuation are inferred.'])
    related=[]; available=True
    if kind=='expense':
        if row.bank_account_id and row.bank_account.user_id!=user.pk: raise Http404
        if row.source=='bank_statement':
            # Keep the bank receipt/revocation boundary; this selector must never bypass review.
            from .hybrid_intelligence import source_context
            source=source_context(user,'bank_statements',transaction_id=row.pk)[0]
            source.update(record_type=kind,record_id=row.pk,as_of=row.transaction_date.isoformat(),
                available=source['data']['verification']=='owner_confirmed')
            source['data'].update(record_type=kind,record_id=row.pk,applicable_date=source['as_of'])
            for field,value in source['data']['amounts'].items():
                value.update(record_type=kind,record_id=row.pk,as_of=source['as_of'],revision=source['revision'],provenance=f'expenses.Expense.{field}; owner-confirmed statement receipt')
            return source
        fields=('amount','closing_balance'); helper=expense_money
        available=(row.source=='manual' and row.amount>0 and row.direction in dict(Expense.DIRECTION_CHOICES)
            and row.classification in dict(Expense.CLASSIFICATION_CHOICES) and row.category in dict(Expense.CATEGORY_CHOICES))
        data.update(transaction_date=row.transaction_date.isoformat(),applicable_date=row.transaction_date.isoformat(),
            direction=row.direction,category=row.category,classification=row.classification)
        if row.source!='manual': data['verification']='imported_not_verified'
    elif kind=='budget':
        fields=('base_budget','inflation_adjusted','spent'); helper=budget_money
        period=_month(row.month); available=period is not None
        data.update(applicable_date=period,month=period,verification='owner_saved_approval_not_recorded')
        data['limitations'].append('Budget has no approval/verification field; saved does not mean independently approved. Spent is the stored field, not a new transaction total.')
        peers=list(Budget.objects.filter(user=user).order_by('pk').values('id','month','base_budget','inflation_adjusted','spent'))
        related=[peer for peer in peers if _month(peer['month'])==period]
        if any(any(peer[field]!=getattr(row,field) for field in fields) for peer in related):
            available=False; data['verification']='conflicting_budget_records'
    elif kind=='loan':
        fields=('principal','emi','remaining_balance','total_paid'); helper=loan_money
        if row.consolidated_into_id and row.consolidated_into.user_id!=user.pk: raise Http404
        if row.source_documents.exclude(user=user).exists(): raise Http404
        if row.payment_history.filter(expense_reference__isnull=False).exclude(expense_reference__user=user).exists(): raise Http404
        available=row.is_confirmed
        data.update(applicable_date=timezone.localdate().isoformat(),start_date=row.start_date.isoformat(),
            status=row.current_status,verification=row.verification_status,verification_source=row.verification_source,
            missed_payments=row.missed_payments,
            last_payment_date=row.last_payment_date.isoformat() if row.last_payment_date else None,
            closed_on=row.closed_on.isoformat() if row.closed_on else None)
        data['limitations'].append('EMI is the persisted contractual installment; no new amortization or payment-date forecast is calculated. Missing remaining balance is unavailable, never principal or zero.')
        latest=row.payment_history.filter(match_status='matched',loan_effect_applied=True).order_by('-payment_date','-pk').first()
        if latest:
            related.append(dict(id=latest.pk,date=latest.payment_date.isoformat(),amount=str(latest.amount),
                remaining_balance=str(latest.remaining_balance),expense=latest.expense_reference_id,
                expense_revision=_digest(Expense.objects.filter(pk=latest.expense_reference_id).values().first())))
            data.update(last_applied_payment_id=latest.pk,last_applied_payment_date=latest.payment_date.isoformat())
        closures=list(row.closure_documents.filter(verification_status='verified').values('id','closure_amount','closure_date'))
        related+=closures
        if ((row.current_status in ('closed','foreclosed','prepaid') and row.remaining_balance not in (None,0)) or
                row.payment_history.filter(loan_effect_applied=True).exclude(match_status='matched').exists() or
                len({(value['closure_amount'],value['closure_date']) for value in closures})>1):
            available=False; data['verification']='conflicting_loan_records'
    else:
        fields=('invested_amount','monthly_sip','current_value'); helper=investment_money
        documents=row.source_documents.all()
        if documents.exclude(user=user).exists(): raise Http404
        from apps.investments.services.document_evidence import evidence
        related=[]; document_sources=[]; confirmed={field:[] for field in fields}
        # shortcut: bound reads to five source files; add explicit selection for larger histories.
        if documents.count()>5:
            available=False
            related=list(documents.order_by('pk').values('id','parser_status','updated_at')[:6])
        else:
            for document in documents.order_by('pk'):
                detail=evidence(user,document.pk,row.pk)
                related.append(dict(id=document.pk,revision=detail['revision'],fields=detail['fields'],source_status=detail['source_status']))
                document_sources.append(dict(document_id=document.pk,url=detail['citation_url'],source_status=detail['source_status']))
                for field in fields:
                    if (detail['fields'][field]['verification']=='owner_confirmed' and
                            detail['fields'][field]['current']==format(helper(getattr(row,field)),'.2f')):
                        confirmed[field].append(document.pk)
        data.update(applicable_date=row.updated_at.isoformat(),asset_type=row.asset_type,market_price_as_of=None,
            verification='source_review_limit' if not available else 'owner_confirmed_document_fields' if all(confirmed.values()) else 'imported_record_not_field_verified' if related else 'user_recorded',
            document_sources=document_sources)
        data['limitations'].append('Portfolio values are recorded positions, not live market quotes. Original import text never overrides a current corrected register value.')
        if related: data['limitations'].append('Field confirmation is the owner\'s attestation, not independent broker authentication. Unconfirmed, unavailable or changed document evidence remains unverified.')
    data['amounts']={field:_amount(getattr(row,field),helper,data['verification'],f'{row._meta.label}.{field}') for field in fields}
    if kind=='investment':
        for field in fields:
            data['amounts'][field].update(source_document_ids=confirmed[field])
            if available and confirmed[field]: data['amounts'][field]['evidence_status']='owner_confirmed_document_field'
    revision_data=dict(owner=row.user_id,record=list(MODELS[kind].objects.filter(pk=row.pk).values())[0],related=related,data=data)
    if not available:
        for value in data['amounts'].values(): value.update(amount=None,evidence_status='unavailable')
    source=_source(kind,row.pk,data,revision_data,available=available)
    if kind=='investment' and len(document_sources)==1 and all(confirmed.values()): source['url']=document_sources[0]['url']
    return source


def choices(user):
    _owner(user)
    return [dict(kind=kind,id=identity,label=f'{kind.title()} record #{identity}') for kind,model in MODELS.items()
        for identity in model.objects.filter(user=user).order_by('-pk').values_list('pk',flat=True)[:20]]+[
            dict(kind='baseline',id=user.pk,label='Reported baseline fields (currency-limited)')]


def supported_question(query):
    # shortcut: fail-closed English record questions; expand only with evaluated intent fixtures.
    text=query.strip().lower().rstrip('?.!')
    if re.search(r'\b(?:total|sum|aggregate|convert|conversion|exchange|fx|forecast|predict|tomorrow|future|weather|buy|sell|approve|approval|authentic|currency|inr|usd|eur|gbp)\b',text): return False
    return bool(re.fullmatch(r'(?:explain|show|review) (?:my |this |the |selected |recorded |canonical |current )*(?:record|records|values|expense|transaction|budget|loan|investment|baseline|emi|repayment status|evidence|provenance|income|rent)(?: details| values| status| and limitations)?',text))
