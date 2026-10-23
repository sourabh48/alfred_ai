"""Read-only individual financial records; unknown currencies never form new totals."""
from datetime import date, datetime, time, timezone as datetime_timezone
from hashlib import sha256
import json
import re

from django.contrib.auth import get_user_model
from django.core import signing
from django.db.models import Count, Max
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
from .persistent_memory import _owner, MemoryConflict

MODELS={'expense':Expense,'budget':Budget,'loan':Loan,'investment':Investment}
KINDS=(*MODELS,'baseline')
BASELINE_KEYS=('monthly_income','liquid_cash','recurring_emi_burden','total_assets','total_liabilities','net_worth')
DOCUMENT_LIMIT=5
CATALOG_SALT='alfred.financial-source-catalog.v1'
PAGE_SALT='alfred.financial-source-page.v1'
DISCOVERY_LIMIT=4096


class SourceSelectionConflict(MemoryConflict):
    pass


def _digest(value):
    return sha256(json.dumps(value,sort_keys=True,allow_nan=False,default=str).encode()).hexdigest()


def _owned_record(user, kind, identity):
    _owner(user)
    if kind not in MODELS or type(identity) is not int or identity<1: raise Http404
    row=get_object_or_404(MODELS[kind],pk=identity,user=user)
    if kind in ('loan','investment') and row.source_documents.exclude(user=user).exists(): raise Http404
    if kind=='loan':
        if row.consolidated_into_id and row.consolidated_into.user_id!=user.pk: raise Http404
        if row.payment_history.filter(expense_reference__isnull=False).exclude(expense_reference__user=user).exists(): raise Http404
    if kind=='expense':
        if row.bank_account_id and row.bank_account.user_id!=user.pk: raise Http404
        if row.source=='bank_statement' and row.statement_upload_id:
            upload=row.statement_upload
            if upload.user_id!=user.pk or (upload.bank_account_id and upload.bank_account.user_id!=user.pk): raise Http404
    return row


def _record_revision(row):
    return _digest({field.attname:getattr(row,field.attname) for field in row._meta.concrete_fields})


def _document_catalog(user, kind, identity):
    row=_owned_record(user,kind,identity)
    if kind in ('loan','investment'):
        manager=row.source_documents
        documents=manager.all()
        # Through-row IDs advance on relinking, including links to older documents.
        membership=manager.through.objects.filter(**{f'{kind}_id':identity}).aggregate(count=Count('pk'),version=Max('pk'))
    elif kind=='expense':
        from apps.expenses.models import StatementUpload
        documents=StatementUpload.objects.filter(pk=row.statement_upload_id,user=user) if row.source=='bank_statement' else StatementUpload.objects.none()
        membership=documents.aggregate(count=Count('pk'),version=Max('pk'))
    else:
        return row,None,None
    return row,documents,dict(owner=user.pk,kind=kind,identity=identity,record=_record_revision(row),membership=membership)


def _load_catalog(token, expected):
    if not isinstance(token,str) or not 1<=len(token)<=4096: raise ValueError('Choose a current financial source list.')
    try: stamp=signing.loads(token,salt=CATALOG_SALT,max_age=900)
    except signing.SignatureExpired as exc: raise SourceSelectionConflict() from exc
    except signing.BadSignature as exc: raise ValueError('Invalid source list.') from exc
    if not isinstance(stamp,dict): raise ValueError('Invalid source list.')
    if any(stamp.get(key)!=expected[key] for key in ('owner','kind','identity')): raise Http404
    if stamp!=expected: raise SourceSelectionConflict()


def _document_evidence(user, kind, row, document):
    if kind=='loan':
        from apps.loans.services.document_evidence import evidence
    elif kind=='investment':
        from apps.investments.services.document_evidence import evidence
    else:
        from apps.expenses.services.statement_evidence import evidence
        return evidence(user,row.pk,document_id=document.pk)
    return evidence(user,document.pk,row.pk)


def _loan_conflict(row, closures):
    return ((row.current_status in ('closed','foreclosed','prepaid') and row.remaining_balance not in (None,0)) or
        row.payment_history.filter(loan_effect_applied=True).exclude(match_status='matched').exists() or
        len({(value['closure_amount'],value['closure_date']) for value in closures})>1)


def _document_item(kind, row, document, detail):
    if kind=='expense':
        verification=detail['verification']
        confirmed=verification=='owner_confirmed'
        available=not verification.startswith('source_')
        name=detail['statement']['document_name']; citation=detail['citation_url']
        uploaded=document.uploaded_at
        confirmed_fields=['transaction'] if confirmed else []
    else:
        confirmed_fields=[key for key,value in detail['fields'].items() if value['verification']=='owner_confirmed']
        confirmed=len(confirmed_fields)==len(detail['fields'])
        available=detail['source_status']=='available'
        verification=('owner_confirmed' if confirmed else 'partially_owner_confirmed' if confirmed_fields else
            'needs_owner_review' if detail['review_allowed'] else 'source_unavailable')
        name=detail['document_name']; citation=detail['citation_url']; uploaded=document.created_at
    # Eligibility is a current field-level preflight, never permission for arbitrary document Q&A.
    record_conflict=kind=='loan' and _loan_conflict(row,row.closure_documents.filter(verification_status='verified').values('closure_amount','closure_date'))
    reason=('source_unavailable' if not available else
        'source_conflict' if record_conflict or verification in ('conflicting_source','conflicting_records','duplicate_records') else
        'document_review_required' if verification=='document_needs_review' or (kind!='expense' and not detail['review_allowed']) else
        'owner_review_required' if not confirmed_fields else
        'record_confirmation_required' if kind=='loan' and not row.is_confirmed else 'reviewed_fields_only')
    eligible=reason=='reviewed_fields_only'
    grounding=dict(status=reason,eligible_fields=confirmed_fields if eligible else [],
        scope='financial_records',full_text_qa=False,
        limitation='Only current owner-reviewed structured fields are eligible. Selection and source revisions are rechecked before and after local inference. '
            'No arbitrary document Q&A, independent bank/broker authentication or inferred currency.')
    return dict(document_id=document.pk,type='bank_statement' if kind=='expense' else f'{kind}_import',name=name,
        uploaded_at=uploaded.isoformat(),verification=verification,confirmed_fields=confirmed_fields,
        freshness='current_review' if confirmed else 'partial_review' if confirmed_fields else 'review_required' if available else 'unavailable',
        source_status=detail.get('source_status',verification),revision=detail['revision'],url=citation,
        selectable=eligible,grounding=grounding)


def document_page(user, kind, identity, *, cursor=None):
    _owner(user)
    if kind=='baseline':
        if type(identity) is not int or identity!=user.pk: raise Http404
        return dict(supported=False,items=[],count=0,next_cursor=None,limit=DOCUMENT_LIMIT)
    row,documents,stamp=_document_catalog(user,kind,identity)
    if documents is None: return dict(supported=False,items=[],count=0,next_cursor=None,limit=DOCUMENT_LIMIT)
    after=0
    if cursor is not None:
        if not isinstance(cursor,str) or not 1<=len(cursor)<=8192: raise ValueError('Invalid source page.')
        try: page=signing.loads(cursor,salt=PAGE_SALT,max_age=900)
        except signing.SignatureExpired as exc: raise SourceSelectionConflict() from exc
        except signing.BadSignature as exc: raise ValueError('Invalid source page.') from exc
        if not isinstance(page,dict) or set(page)!= {'catalog','after'} or type(page['after']) is not int or page['after']<0:
            raise ValueError('Invalid source page.')
        token=page['catalog']; after=page['after']; _load_catalog(token,stamp)
    else: token=signing.dumps(stamp,salt=CATALOG_SALT,compress=True)
    rows=list(documents.filter(pk__gt=after).order_by('pk')[:DOCUMENT_LIMIT+1]); items=[]
    from alfred_ai.services.upload_limits import UploadLimitExceeded
    from apps.expenses.services.statement_evidence import document_name
    for document in rows[:DOCUMENT_LIMIT]:
        try: items.append(_document_item(kind,row,document,_document_evidence(user,kind,row,document)))
        except UploadLimitExceeded:
            items.append(dict(document_id=document.pk,type='bank_statement' if kind=='expense' else f'{kind}_import',
                name=document_name(document),uploaded_at=(document.uploaded_at if kind=='expense' else document.created_at).isoformat(),
                verification='processing_limit',freshness='unavailable',selectable=False,revision=None,url=None,confirmed_fields=[]))
    if _document_catalog(user,kind,identity)[2]!=stamp: raise SourceSelectionConflict()
    return dict(supported=True,items=items,count=stamp['membership']['count'],limit=DOCUMENT_LIMIT,catalog_token=token,
        page_cursor=signing.dumps(dict(catalog=token,after=after),salt=PAGE_SALT),
        checked_at=timezone.now().isoformat(),next_cursor=signing.dumps(dict(catalog=token,after=rows[DOCUMENT_LIMIT-1].pk),salt=PAGE_SALT)
        if len(rows)>DOCUMENT_LIMIT else None)


def _discovery_filters(filters):
    if filters is None: filters={}
    if not isinstance(filters,dict) or set(filters)-{'name','date_from','date_to'}: raise ValueError('Invalid document filters.')
    result={key:filters.get(key,'') for key in ('name','date_from','date_to')}
    if (any(not isinstance(value,str) for value in result.values()) or len(result['name'])>128
            or len(result['name'].encode())>512 or any(ord(char)<32 or ord(char)==127 for char in result['name'])):
        raise ValueError('Choose a bounded document name and ISO date range.')
    result['name']=result['name'].strip().casefold()
    for key in ('date_from','date_to'):
        value=result[key]
        if value:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value): raise ValueError('Use YYYY-MM-DD upload dates.')
            date.fromisoformat(value)
    if result['date_from'] and result['date_to'] and result['date_from']>result['date_to']: raise ValueError('Upload date range is reversed.')
    return result


def _discovery_catalog(user, kind, document_id, filters=None):
    from apps.expenses.models import StatementUpload
    from apps.investments.models import InvestmentImportDocument
    from apps.loans.models import LoanImportDocument
    from apps.expenses.services.statement_evidence import file_reference, document_name
    model={'expense':StatementUpload,'loan':LoanImportDocument,'investment':InvestmentImportDocument}.get(kind)
    if model is None: raise Http404
    document=None; links=None; metadata=None
    if document_id is None:
        filters=_discovery_filters(filters)
        rows=model.objects.filter(user=user)
        date_field='uploaded_at' if kind=='expense' else 'created_at'
        rows=rows.only('pk','user_id','file_name',date_field)
        for key,lookup,boundary in (('date_from','gte',time.min),('date_to','lte',time.max)):
            if filters[key]: rows=rows.filter(**{date_field+'__'+lookup:datetime.combine(date.fromisoformat(filters[key]),boundary,tzinfo=datetime_timezone.utc)})
        candidates=list(rows.order_by('pk')[:DISCOVERY_LIMIT+1])
        if len(candidates)>DISCOVERY_LIMIT: raise ValueError('Document discovery exceeds its bounded record limit. Narrow the upload-date range.')
        # Match the displayed basename, never an internal directory or a truncated page.
        candidates=[row for row in candidates if filters['name'] in document_name(row).casefold()]
        identities=[row.pk for row in candidates]
        metadata=_digest([(row.pk,row.file_name,getattr(row,date_field)) for row in candidates])
        rows=rows.filter(pk__in=identities)
        source=None
    else:
        document=get_object_or_404(model,user=user,pk=document_id)
        rows=document.expenses.all() if kind=='expense' else getattr(document,f'linked_{kind}s').all()
        if rows.exclude(user=user).exists(): raise Http404
        if kind=='expense':
            if document.bank_account_id and document.bank_account.user_id!=user.pk: raise Http404
            rows=rows.filter(source='bank_statement')
        else:
            manager=getattr(document,f'linked_{kind}s')
            links=manager.through.objects.filter(**{manager.source_field_name+'_id':document.pk}).aggregate(count=Count('pk'),version=Max('pk'))
        source=dict(record=_record_revision(document),file=list(file_reference(document.original_file if kind=='expense' else document.uploaded_file)[:2]))
        identities=list(rows.order_by('pk').values_list('pk',flat=True)[:DISCOVERY_LIMIT+1])
        if len(identities)>DISCOVERY_LIMIT: raise ValueError('Document discovery exceeds its bounded record limit.')
    stamp=dict(owner=user.pk,kind=kind,identity=document_id,purpose='document-discovery-v1',source=source,membership=_digest(identities),links=links)
    if document_id is None: stamp.update(filters=_digest(filters),metadata=metadata)
    return document,rows,stamp,len(identities)


def document_record_page(user, kind, document_id=None, *, cursor=None, filters=None):
    """Owner-directed discovery only; existing evidence pages retain correction authority."""
    from apps.expenses.services.statement_evidence import document_name
    from alfred_ai.services.upload_limits import UploadLimitExceeded
    _owner(user)
    if document_id is not None and filters is not None: raise ValueError('Filters apply to the document list, not linked records.')
    document,rows,stamp,count=_discovery_catalog(user,kind,document_id,filters)
    after=0
    if cursor is not None:
        if not isinstance(cursor,str) or not 1<=len(cursor)<=8192: raise ValueError('Invalid document discovery page.')
        try: page=signing.loads(cursor,salt=PAGE_SALT,max_age=900)
        except signing.SignatureExpired as exc: raise SourceSelectionConflict() from exc
        except signing.BadSignature as exc: raise ValueError('Invalid document discovery page.') from exc
        if not isinstance(page,dict) or set(page)!={'catalog','after'} or type(page['after']) is not int or page['after']<0: raise ValueError('Invalid document discovery page.')
        token=page['catalog']; after=page['after']; _load_catalog(token,stamp)
    else: token=signing.dumps(stamp,salt=CATALOG_SALT,compress=True)
    selected=list(rows.filter(pk__gt=after).order_by('pk')[:DOCUMENT_LIMIT+1]); items=[]; revisions=[]
    for row in selected[:DOCUMENT_LIMIT]:
        if document is None:
            items.append(dict(document_id=row.pk,name=document_name(row),type='bank_statement' if kind=='expense' else f'{kind}_import',
                uploaded_at=(row.uploaded_at if kind=='expense' else row.created_at).isoformat(),verification='not_checked',full_text_qa=False))
        else:
            _owned_record(user,kind,row.pk)
            try:
                detail=_document_evidence(user,kind,row,document)
                item=_document_item(kind,row,document,detail)
                revisions.append((row.pk,dict(item)))
                item.update(record_type=kind,record_id=row.pk,original_evidence=detail['original_status'] if kind=='expense' else
                    {key:value['original_status'] for key,value in detail['fields'].items()})
                items.append(item)
            except UploadLimitExceeded:
                items.append(dict(record_type=kind,record_id=row.pk,selectable=False,url=None,verification='processing_limit',grounding=None))
    # A displayed attestation must still describe this exact owner/document/record revision.
    for identity,expected in revisions:
        current=_owned_record(user,kind,identity)
        if _document_item(kind,current,document,_document_evidence(user,kind,current,document))!=expected: raise SourceSelectionConflict()
    if _discovery_catalog(user,kind,document_id,filters)[2]!=stamp: raise SourceSelectionConflict()
    return dict(level='documents' if document is None else 'records',kind=kind,document_id=document_id,
        document_name=document_name(document) if document else None,items=items,count=count,limit=DOCUMENT_LIMIT,
        checked_at=timezone.now().isoformat(),full_text_qa=False,
        limitation='Discovery is not document authentication or financial advice. Review current corrected values and separately retained original evidence; no currency is inferred.',
        catalog_token=token,page_cursor=signing.dumps(dict(catalog=token,after=after),salt=PAGE_SALT),
        next_cursor=signing.dumps(dict(catalog=token,after=selected[DOCUMENT_LIMIT-1].pk),salt=PAGE_SALT) if len(selected)>DOCUMENT_LIMIT else None)


def document_record_sources(user, kind, document_id, selection, token):
    """Current reviewed projections only; never combine money or extract arbitrary text."""
    _owner(user)
    if kind not in ('expense','loan','investment') or type(document_id) is not int or document_id<1: raise Http404
    if (not isinstance(selection,list) or not 1<=len(selection)<=3
            or any(not isinstance(item,dict) or set(item)!={'id','revision'} or type(item['id']) is not int or item['id']<1
                or not isinstance(item['revision'],str) or not re.fullmatch('[a-f0-9]{64}',item['revision']) for item in selection)
            or len({item['id'] for item in selection})!=len(selection)):
        raise ValueError('Choose one to three distinct currently reviewed records.')
    def read():
        document,rows,stamp,_=_discovery_catalog(user,kind,document_id)
        _load_catalog(token,stamp)
        if rows.filter(pk__in=[item['id'] for item in selection]).count()!=len(selection): raise Http404
        result=[]
        for chosen in sorted(selection,key=lambda item:item['id']):
            row=_owned_record(user,kind,chosen['id'])
            detail=_document_evidence(user,kind,row,document)
            item=_document_item(kind,row,document,detail)
            if detail['revision']!=chosen['revision'] or not item['selectable']: raise SourceSelectionConflict()
            _,_,record_stamp=_document_catalog(user,kind,row.pk)
            source=record_source(user,kind,row.pk,selected_documents=[dict(id=document_id,revision=chosen['revision'])],
                source_catalog=signing.dumps(record_stamp,salt=CATALOG_SALT,compress=True))
            if not source['available']: raise SourceSelectionConflict()
            fields=('amount','closing_balance') if kind=='expense' else item['grounding']['eligible_fields']
            excluded={key:'not_recorded' if value['amount'] is None else 'not_reviewed_from_selected_document'
                for key,value in source['data']['amounts'].items() if key not in fields}
            source['data']['amounts']={key:value for key,value in source['data']['amounts'].items() if key in fields}
            if not any(value['amount'] is not None for value in source['data']['amounts'].values()): raise SourceSelectionConflict()
            source['data']={key:value for key,value in source['data'].items() if key in ('record_type','record_id','applicable_date',
                'transaction_date','original_transaction_date','original_status','category','classification',
                'statement_start','statement_end','original_statement_start','original_statement_end',
                'provenance','amounts','limitations','document_sources','document_selection')}
            source.update(url=item['url'],document_id=document_id,classification='owner_reviewed_document_record')
            source['data'].update(document_name=item['name'],document_id=document_id,verification='owner_confirmed_document_fields',unreviewed_fields=excluded)
            source['data']['limitations'].append('Only reviewed fields from this selected document are shown separately. No combined amount, currency, independent authenticity or arbitrary document text is established.')
            result.append(source)
        if _discovery_catalog(user,kind,document_id)[2]!=stamp: raise SourceSelectionConflict()
        return result
    result=read()
    if read()!=result: raise SourceSelectionConflict()
    return result


def _selected_documents(user, kind, row, selection, token):
    if (kind not in ('expense','loan','investment') or not isinstance(selection,list) or not 1<=len(selection)<=DOCUMENT_LIMIT
            or any(not isinstance(item,dict) or set(item)!= {'id','revision'} or type(item['id']) is not int or item['id']<1
                or not isinstance(item['revision'],str) or not re.fullmatch('[a-f0-9]{64}',item['revision']) for item in selection)
            or len({item['id'] for item in selection})!=len(selection)):
        raise ValueError('Choose one to five distinct reviewed financial sources.')
    current,documents,stamp=_document_catalog(user,kind,row.pk)
    _load_catalog(token,stamp)
    if _record_revision(row)!=_record_revision(current): raise SourceSelectionConflict()
    chosen={item['id']:item['revision'] for item in selection}
    rows=list(documents.filter(pk__in=chosen).order_by('pk'))
    if len(rows)!=len(chosen): raise Http404
    details={}; fingerprints=set()
    for document in rows:
        detail=_document_evidence(user,kind,row,document)
        if detail['revision']!=chosen[document.pk] or not _document_item(kind,row,document,detail)['selectable']:
            raise SourceSelectionConflict()
        fingerprint=detail.get('source_fingerprint')
        if fingerprint and fingerprint in fingerprints: raise SourceSelectionConflict()
        if fingerprint: fingerprints.add(fingerprint)
        details[document.pk]=detail
    if _document_catalog(user,kind,row.pk)[2]!=stamp: raise SourceSelectionConflict()
    return rows,details,dict(mode='explicit',selected_count=len(rows),linked_count=stamp['membership']['count'],
        unselected_count=stamp['membership']['count']-len(rows),limit=DOCUMENT_LIMIT)


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


def record_source(user, kind, identity, *, selected_documents=None, source_catalog=None):
    _owner(user)
    if kind not in KINDS or type(identity) is not int or identity<1: raise Http404
    if kind=='baseline':
        if selected_documents is not None or source_catalog is not None: raise ValueError('This record has no document selection.')
        if identity!=user.pk: raise Http404
        return baseline_source(user)
    row=_owned_record(user,kind,identity)
    selection=None; selected_rows=None; selected_details={}
    if selected_documents is not None or source_catalog is not None:
        selected_rows,selected_details,selection=_selected_documents(user,kind,row,selected_documents,source_catalog)
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
            if selection:
                detail=selected_details[row.statement_upload_id]
                if source['revision']!=detail['revision']: raise SourceSelectionConflict()
                source['data'].update(document_selection=selection,document_sources=[_document_item(kind,row,selected_rows[0],detail)])
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
            reference=dict(transaction_id=None,url=None,verification='source_not_retained',
                evidence_status='unavailable',revision=None)
            expense=Expense.objects.filter(pk=latest.expense_reference_id,user=user).first()
            if latest.expense_reference_id and expense is None and Expense.objects.filter(pk=latest.expense_reference_id).exists(): raise Http404
            if expense:
                if expense.bank_account_id and expense.bank_account.user_id!=user.pk: raise Http404
                reference['transaction_id']=expense.pk
                if expense.source!='bank_statement' or expense.statement_upload_id is not None:
                    transaction_source=record_source(user,'expense',expense.pk)
                    reference.update(url=transaction_source['url'],revision=transaction_source['revision'],
                        verification=transaction_source['data']['verification'],
                        evidence_status='owner_confirmed_statement_reference' if transaction_source.get('available')
                            and transaction_source['classification']=='owner_confirmed_statement_record' else
                            'owner_recorded_transaction_reference' if transaction_source.get('available') else 'unverified_transaction_reference')
            related.append(dict(id=latest.pk,date=latest.payment_date.isoformat(),amount=str(latest.amount),
                remaining_balance=str(latest.remaining_balance),expense=latest.expense_reference_id,
                expense_revision=_digest(Expense.objects.filter(pk=latest.expense_reference_id).values().first()),
                transaction_source=reference))
            data.update(last_applied_payment_id=latest.pk,last_applied_payment_date=latest.payment_date.isoformat(),
                applied_payment_source=reference)
            data['limitations'].append('The applied-payment transaction link is a recorded association only. It does not verify matching amounts/dates, settlement allocations or bank authenticity; no payment total is recalculated.')
        closures=list(row.closure_documents.filter(verification_status='verified').values('id','closure_amount','closure_date'))
        related+=closures
        if _loan_conflict(row,closures):
            available=False; data['verification']='conflicting_loan_records'
    else:
        fields=('invested_amount','monthly_sip','current_value'); helper=investment_money
        data.update(applicable_date=row.updated_at.isoformat(),asset_type=row.asset_type,market_price_as_of=None)
        data['limitations'].append('Portfolio values are recorded positions, not live market quotes. Original import text never overrides a current corrected register value.')
    if kind in ('loan','investment'):
        documents=row.source_documents.all()
        if documents.exclude(user=user).exists(): raise Http404
        if kind=='loan':
            from apps.loans.services.document_evidence import evidence, FIELDS
            proof_fields=FIELDS
        else:
            from apps.investments.services.document_evidence import evidence
            proof_fields=fields
        document_sources=[]; confirmed={field:[] for field in proof_fields}
        source_limit=selection is None and documents.count()>DOCUMENT_LIMIT
        if source_limit:
            available=False
            related+=list(documents.order_by('pk').values('id','parser_status')[:6])
            data['limitations'].append('More than five source documents require explicit source selection before answering.')
        else:
            for document in selected_rows if selection else documents.order_by('pk'):
                detail=selected_details[document.pk] if selection else evidence(user,document.pk,row.pk)
                related.append(dict(id=document.pk,revision=detail['revision'],fields=detail['fields'],source_status=detail['source_status']))
                document_sources.append(_document_item(kind,row,document,detail))
                for field in proof_fields:
                    if (getattr(row,field) is not None and detail['fields'][field]['verification']=='owner_confirmed' and
                            detail['fields'][field]['current']==format(helper(getattr(row,field)),'.2f')):
                        confirmed[field].append(document.pk)
        document_verification=('source_review_limit' if source_limit else 'owner_confirmed_document_fields' if all(confirmed.values())
            else 'imported_record_not_field_verified' if document_sources else 'user_recorded')
        data.update(document_sources=document_sources,document_verification=document_verification)
        if selection:
            data['document_selection']=selection
            data['limitations'].append('Only the explicitly selected document revisions were used. Unselected documents were not read or represented as reviewed; selected evidence never establishes independent bank/broker authenticity.')
        if kind=='investment': data['verification']=document_verification
        if document_sources:
            data['limitations'].append('Field confirmation is the owner\'s attestation, not independent bank/broker authentication. Current register corrections take precedence; unconfirmed, unavailable or changed document evidence remains unverified.')
    data['amounts']={field:_amount(getattr(row,field),helper,data['verification'],f'{row._meta.label}.{field}') for field in fields}
    if kind in ('loan','investment'):
        for field in fields:
            data['amounts'][field].update(source_document_ids=confirmed.get(field,[]))
            if available and confirmed.get(field): data['amounts'][field]['evidence_status']='owner_confirmed_document_field'
    revision_data=dict(owner=row.user_id,record=list(MODELS[kind].objects.filter(pk=row.pk).values())[0],related=related,data=data)
    if not available:
        for value in data['amounts'].values(): value.update(amount=None,evidence_status='unavailable')
    source=_source(kind,row.pk,data,revision_data,available=available)
    if kind in ('loan','investment') and available and len(document_sources)==1 and all(confirmed.values()):
        source['url']=document_sources[0]['url']
    return source


def choices(user):
    _owner(user)
    return [dict(kind=kind,id=identity,label=f'{kind.title()} record #{identity}') for kind,model in MODELS.items()
        for identity in model.objects.filter(user=user).order_by('-pk').values_list('pk',flat=True)[:20]]+[
            dict(kind='baseline',id=user.pk,label='Reported baseline fields (currency-limited)')]


def requested_record_field(query, *, kind):
    fields={'expense':('amount','closing_balance','transaction_date','category','classification','statement_period'),'loan':('principal','emi','remaining_balance'),
        'investment':('invested_amount','monthly_sip','current_value')}
    text=query.strip().lower().rstrip('?.!')
    if kind=='expense' and re.fullmatch(r'(?:what (?:period|dates) does (?:this|the|my|selected|the selected) statement cover|when does (?:this|the|my|selected|the selected) statement start and end|what are (?:the |my |selected )?statement dates)',text):
        return 'statement_period'
    match=re.fullmatch(r'(?:explain|show|review|what is|what are) (?:my |this |the |selected |recorded |canonical |current )*(amount|closing balance|principal|emi|remaining balance|invested amount|monthly sip|current value|transaction dates?|category|classification|statement period|statement date range)(?: details| values| status| and limitations)?',text)
    field=match[1].replace(' ','_') if match else None
    if field=='transaction_dates': field='transaction_date'
    if field=='statement_date_range': field='statement_period'
    if text.startswith('what are ') and field!='transaction_date': return None
    return field if field in fields.get(kind,()) else None


def supported_question(query, *, kind=None):
    # shortcut: fail-closed English record questions; expand only with evaluated intent fixtures.
    text=query.strip().lower().rstrip('?.!')
    if re.search(r'\b(?:total|sum|aggregate|convert|conversion|exchange|fx|forecast|predict|tomorrow|future|weather|buy|sell|approve|approval|authentic|currency|inr|usd|eur|gbp)\b',text): return False
    if requested_record_field(query,kind=kind): return True
    match=re.fullmatch(r'(?:explain|show|review) (?:my |this |the |selected |recorded |canonical |current )*(?P<subject>record|records|values|expense|transaction|budget|loan|investment|baseline|emi|repayment status|evidence|provenance|income|rent|(?:source |statement )(?:record|transaction))(?: details| values| status| and limitations)?',text)
    if not match: return False
    if kind is None: return True
    subjects={'expense':('expense','transaction','source transaction','source record','statement record','statement transaction'),'budget':('budget',),'loan':('loan','emi','repayment status'),
        'investment':('investment',),'baseline':('baseline','income','rent')}
    return kind in subjects and match['subject'] in ('record','records','values','evidence','provenance',*subjects[kind])
