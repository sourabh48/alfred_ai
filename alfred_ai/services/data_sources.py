"""Owned source inventory; saved records and parser success never imply verification."""
from django.db import DatabaseError
from django.db.models import Count, Max, Q

from apps.budgets.models import Budget, SavingsGoal
from apps.career.models import CareerProfile, CareerResume
from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanImportDocument
from apps.mobility.models import BikeProfile, TravelPlan, TravelPreferenceProfile


def data_sources_snapshot(user):
    groups = [
        ('Finance', [(BankAccount, 'Bank accounts'), (Expense, 'Transactions')], StatementUpload, 'uploaded_at',
         [('Income and preferences', '/settings/'), ('Accounts and statements', '/expenses/')]),
        ('Loans', [(Loan, 'Loans')], LoanImportDocument, 'created_at', [('Loans and EMI documents', '/loans/')]),
        ('Budgets and goals', [(Budget, 'Budgets'), (SavingsGoal, 'Savings goals')], None, None,
         [('Budgets and savings goals', '/budgets/')]),
        ('Investments', [(Investment, 'Holdings')], InvestmentImportDocument, 'updated_at',
         [('Holdings and statement imports', '/investments/')]),
        ('Career', [(CareerProfile, 'Professional profiles')], CareerResume, 'updated_at',
         [('Profile, resume and applications', '/career/')]),
        ('Travel', [(BikeProfile, 'Vehicles'), (TravelPlan, 'Saved trips')], None, None,
         [('Plan and reopen trips', '/mobility/'), ('Vehicle profile', '/bike-service/')]),
    ]
    sources = []
    for label, models, document_model, timestamp, links in groups:
        source = dict(label=label, links=links, records=[], state='Needs data', has_data=False,
                      imports=None, provenance='Your saved ALFRED records and local uploads.')
        try:
            source['records'] = [dict(label=name, count=model.objects.filter(user=user).count()) for model, name in models]
            source['has_data'] = any(item['count'] for item in source['records'])
            if document_model:
                source['imports'] = document_model.objects.filter(user=user).aggregate(
                    total=Count('pk'), parsed=Count('pk', filter=Q(parser_status='parsed')),
                    awaiting_review=Count('pk', filter=Q(parser_status__in=['pending', 'needs_review'])),
                    failed=Count('pk', filter=Q(parser_status='failed')),
                    last_parsed=Max(timestamp, filter=Q(parser_status='parsed')))
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
            source.update(state='Unavailable', records=[], imports=None, has_data=False)
        sources.append(source)
    return dict(sources=sources, populated=sum(item['has_data'] for item in sources), total=len(sources))
