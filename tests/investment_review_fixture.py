"""Explicit owner confirmation of isolated synthetic fixtures; never used by runtime code."""
from apps.investments.models import InvestmentImportDocument
from apps.investments.services.import_review import investment_preview, edit_investment_review, confirm_investment_review, FIELDS


def confirm_fixture(user, document):
    for page in range(1, investment_preview(document)['pages'] + 1):
        preview = investment_preview(document, page=page)
        edits = []
        for row in preview['rows']:
            if row['action'] != 'create': continue
            # These are deliberate test-owner choices, not parser defaults.
            data = {key: row.get(key) for key in FIELDS}
            for key, default in dict(asset_type='equity', monthly_sip='0', annual_return_rate='0',
                                     invested_amount='0', current_value='0', currency='INR').items():
                if data[key] in (None, ''): data[key] = default
            edits.append(dict(index=row['index'], **data))
        document = edit_investment_review(document, revision=preview['revision'], edits=edits)
    return confirm_investment_review(document, token=investment_preview(document)['token'])


def confirm_response(client, response):
    from django.contrib.auth import get_user_model
    if response.status_code != 201: return response
    document = InvestmentImportDocument.objects.get(pk=response.json()['upload']['id'])
    confirm_fixture(get_user_model().objects.get(pk=document.user_id), document)
    return response
