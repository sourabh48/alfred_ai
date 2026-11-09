from django.contrib.auth.decorators import login_required
from django.db import OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.expenses.models import StatementUpload
from apps.expenses.money import expense_money
from apps.expenses.services.statement_review import (
    StatementReviewConflict, confirm_statement, edit_statement_preview, statement_preview,
)


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def statement_review_view(request, pk):
    upload = get_object_or_404(StatementUpload, pk=pk, user=request.user)
    error = ''
    response_status = 200
    try:
        page = int(request.POST.get('page', request.GET.get('page', '1')))
        preview = statement_preview(upload, page=page)
    except (ValueError, TypeError):
        preview = None
        error = 'No current preview is available. Retry this source from Documents.'
        response_status = 409
    if request.method == 'POST' and preview:
        try:
            edits = []
            for row in preview['rows']:
                edit = {'index': row['index']}
                for field in ('amount', 'closing_balance', 'transaction_date', 'direction'):
                    name = f"row-{row['index']}-{field}"
                    value = request.POST.get(name, '')
                    current = row[field]
                    if field in ('amount', 'closing_balance'):
                        value = None if value == '' and field == 'closing_balance' else str(expense_money(value))
                        current = None if current is None else str(expense_money(current))
                    if value != current:
                        edit[field] = value
                if len(edit) > 1:
                    edits.append(edit)
            account_number = request.POST.get('account_number', '')
            if request.POST.get('action') == 'confirm' and not edits and account_number == preview['account_number']:
                if request.POST.get('reviewed') != 'yes':
                    raise ValueError()
                confirm_statement(upload, token=request.POST.get('token'))
            else:
                edit_statement_preview(upload, revision=int(request.POST.get('revision', '-1')),
                                       edits=edits, account_number=account_number)
            return redirect(f'/expenses/uploads/{pk}/review/?page={page}')
        except (StatementReviewConflict, OperationalError):
            error = 'The preview or account changed. Your input is preserved below; reload and review before confirming.'
            response_status = 409
        except (ValueError, TypeError):
            error = 'Check the account, row values and review checkbox. Save corrections before confirming.'
            response_status = 400
        for row in preview['rows']:
            for field in ('amount', 'closing_balance', 'transaction_date', 'direction'):
                row[field] = request.POST.get(f"row-{row['index']}-{field}", row[field])
        preview['account_number'] = request.POST.get('account_number', preview['account_number'])
        preview['can_confirm'] = False
    return render(request, 'expenses/statement_review.html', {'upload': upload, 'preview': preview,
        'review_error': error}, status=response_status)
