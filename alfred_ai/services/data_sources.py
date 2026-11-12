"""Owned source inventory; saved records and parser success never imply verification."""
from django.db import DatabaseError
from django.db.models import Count, Max, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.budgets.models import Budget, SavingsGoal
from apps.career.models import CareerProfile, CareerResume
from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanImportDocument
from apps.mobility.models import BikeProfile, TravelPlan, TravelPreferenceProfile


# Every place ALFRED reads a web page rather than a free API or official download. Owner rule (2026-11-12):
# read a site's pages only where its data is not available free. tests/test_data_sources.py fails when code
# starts accepting HTML responses in a file that is not listed here.
PUBLIC_PAGE_READS = (
    dict(module='Career', file='apps/career/services/job_intelligence.py',
         what='A job page whose link you paste, when the job site has no free job API. Greenhouse, Lever and Ashby '
              'jobs come from their free public APIs instead.',
         sent='The link you pasted', safeguard="Only on your request, and only if the site's robots.txt allows it."),
    dict(module='Travel', file='apps/mobility/services/travel/providers/web.py',
         what="A guide-listed hotel's own website, for the details it publishes about itself.",
         sent="The hotel's website address", safeguard="Only when you ask for that hotel; robots.txt is checked first."),
    dict(module='Tax', file='apps/integrations/services/verified_intelligence.py',
         what='The official Union Budget website (indiabudget.gov.in), to notice a new Budget year.',
         sent='Nothing about you', safeguard='It has no API. Used as a notice only; tax rules are not changed from it.'),
    dict(module='Investments', file='apps/investments/services/portfolio_intelligence.py',
         what="AMFI's official NAV history download (portal.amfiindia.com).",
         sent='The date range', safeguard='A free official text download that the server may label as a web page.'),
)


def knowledge_sources_snapshot(user):
    """Explicit owner check: metadata only, using existing retention/source validation."""
    from datetime import datetime
    from pathlib import Path
    from django.conf import settings
    from apps.ml_engine.services.document_corpus import DocumentCorpus
    from apps.ml_engine.services.persistent_memory import MemoryStore

    unavailable = {'state': 'Unavailable'}
    try:
        directory = Path(settings.ALFRED_MEMORY_DIR)
        database = directory / 'verified.sqlite3'
        key = directory / 'journal.key'
        if not database.exists() and not key.exists():
            return {'state': 'Not configured'}
        if not database.is_file() or not key.is_file():
            return unavailable
        store = MemoryStore(directory)
        documents = DocumentCorpus(store).list(user)
        memories = store.list_memories(user)
        return {
            'state': 'Checked locally',
            'documents': len(documents['documents']),
            'memories': len(memories),
            'last_document': max((datetime.fromisoformat(r['created_at']) for r in documents['documents']), default=None),
            'last_memory': max((datetime.fromisoformat(r['verified_at']) for r in memories), default=None),
            'memory_retention_days': store.retention_days(user),
            'document_retention_days': documents['maximum_retention_days'],
        }
    except Exception:
        # Corrupt/private storage errors must not expose paths, keys or source contents.
        return unavailable


def data_sources_snapshot(user):
    checked_at = timezone.now()
    groups = [
        ('Finance', [(BankAccount, 'Bank accounts'), (Expense, 'Transactions')], StatementUpload, 'uploaded_at',
         [('Income and preferences', '/settings/'), ('Accounts and statements', '/expenses/')]),
        ('Loans', [(Loan, 'Loans')], LoanImportDocument, 'created_at', [('Loans and EMI documents', '/loans/')]),
        ('Budgets and goals', [(Budget, 'Budgets'), (SavingsGoal, 'Savings goals')], None, None,
         [('Budgets and savings goals', '/budgets/')]),
        ('Investments', [(Investment, 'Holdings')], InvestmentImportDocument, 'updated_at',
         [('Holdings and statement imports', '/investments/')]),
        ('Career', [(CareerProfile, 'Profiles with a role or skills')], CareerResume, 'updated_at',
         [('Profile, resume and applications', '/career/')]),
        ('Travel', [(BikeProfile, 'Vehicles'), (TravelPlan, 'Saved trips')], None, None,
         [('Plan and reopen trips', '/mobility/'), ('Vehicle profile', '/bike-service/')]),
    ]
    sources = []
    for label, models, document_model, timestamp, links in groups:
        source = dict(label=label, links=links, records=[], state='Needs data', has_data=False, reviews=[],
                      imports=None, provenance='Your saved ALFRED records and local uploads.')
        try:
            for model, name in models:
                owned = model.objects.filter(user=user)
                if model is CareerProfile:
                    profile = owned.values('role', 'skills').first()
                    count = int(bool(profile and any((profile[field] or '').strip() for field in ('role', 'skills'))))
                else:
                    count = owned.count()
                source['records'].append(dict(label=name, count=count))
            source['has_data'] = any(item['count'] for item in source['records'])
            if document_model:
                documents = document_model.objects.filter(user=user)
                source['imports'] = documents.aggregate(
                    total=Count('pk'), parsed=Count('pk', filter=Q(parser_status='parsed')),
                    awaiting_review=Count('pk', filter=(Q(parser_status__in=['pending', 'needs_review']) &
                        (Q(extracted_payload__import_review__state__isnull=True) | ~Q(extracted_payload__import_review__state='confirmed')))
                        | Q(extracted_payload__import_review__state='pending')),
                    failed=Count('pk', filter=Q(parser_status='failed')),
                    last_parsed=Max(timestamp, filter=Q(parser_status='parsed')))
                review_prefix = {StatementUpload: '/expenses/uploads/', LoanImportDocument: '/loans/import-uploads/',
                                 InvestmentImportDocument: '/investments/import-uploads/'}.get(document_model)
                if review_prefix:
                    source['imports']['confirmed'] = documents.filter(extracted_payload__import_review__state='confirmed').count()
                    for pk, uploaded_at, raw in documents.filter(extracted_payload__import_review__state='pending') \
                            .order_by('-pk').values_list('pk', timestamp, 'extracted_payload__import_review__expires_at')[:3]:
                        expiry = None
                        if isinstance(raw, str) and len(raw) <= 64:
                            try:
                                expiry = parse_datetime(raw)
                            except ValueError:
                                pass
                        if expiry is not None and timezone.is_naive(expiry):
                            expiry = None
                        status = 'Expiry unavailable'
                        if expiry:
                            status = 'Expired' if expiry <= checked_at else 'Awaiting review'
                        source['reviews'].append(dict(url=f'{review_prefix}{pk}/review/', uploaded_at=uploaded_at,
                            expires_at=expiry, status=status))
                if label == 'Career':
                    source['has_data'] = source['has_data'] or source['imports']['parsed'] > 0
            if label == 'Travel':
                preferences = TravelPreferenceProfile.objects.filter(user=user).values_list('preferences', flat=True).first()
                source['preferences_saved'] = bool(preferences)
                source['has_data'] = source['has_data'] or bool(preferences)
            source['state'] = 'Saved data available' if source['has_data'] else 'Needs data'
            if source['imports'] and source['imports']['awaiting_review']:
                source['state'] = 'Review needed'
            if source['imports'] and source['imports']['failed']:
                source['state'] = 'Import needs attention'
        except DatabaseError:
            source.update(state='Unavailable', records=[], imports=None, has_data=False, reviews=[])
        if source['state'] == 'Unavailable':
            source['next_action'] = dict(label='Check local application diagnostics', url='/settings/diagnostics/')
        elif source['state'] == 'Import needs attention':
            source['next_action'] = dict(label='Check source issues in Documents', url='/documents/')
        elif source['reviews']:
            source['next_action'] = dict(label='Reopen expired review' if source['reviews'][0]['status'] == 'Expired'
                else 'Review the latest extraction', url=source['reviews'][0]['url'])
        elif source['state'] == 'Review needed':
            source['next_action'] = dict(label='Review extracted information', url='/documents/')
        elif not source['has_data']:
            source['next_action'] = dict(label=f'Add {label.lower()} data', url=links[0][1])
        sources.append(source)
    next_setup = next((s for s in sources if s['state'] in ('Unavailable', 'Import needs attention', 'Review needed')), None)
    if next_setup is None:
        next_setup = next((s for s in sources if not s['has_data']), None)
    return dict(sources=sources, populated=sum(item['has_data'] for item in sources), total=len(sources), next_setup=next_setup,
                page_reads=PUBLIC_PAGE_READS)
