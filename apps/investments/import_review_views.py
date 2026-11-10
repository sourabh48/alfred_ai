from django.contrib.auth.decorators import login_required
from django.db import OperationalError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.services.currency import CURRENCY_CHOICES
from .models import Investment, InvestmentImportDocument
from .money import investment_money
from .services.import_review import FIELDS, MONEY, InvestmentReviewConflict, investment_preview, edit_investment_review, confirm_investment_review


class InvestmentImportReviewAPI(APIView):
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        return response

    def get(self, request, pk):
        document = get_object_or_404(InvestmentImportDocument, user=request.user, pk=pk)
        try:
            preview = investment_preview(document, page=int(request.query_params.get('page', '1')))
            return Response({key: value for key, value in preview.items() if key != 'binding'})
        except (ValueError, TypeError):
            return Response({'detail': 'This review is unavailable. Retry the retained source.'}, status=409)

    def patch(self, request, pk):
        data = request.data
        if not isinstance(data, dict) or set(data) != {'revision', 'edits'}:
            return Response({'detail': 'Submit the review revision and supported row edits.'}, status=400)
        try:
            document = get_object_or_404(InvestmentImportDocument, user=request.user, pk=pk)
            edit_investment_review(document, revision=data['revision'], edits=data['edits'])
            return Response({'saved': True})
        except (InvestmentReviewConflict, OperationalError):
            return Response({'detail': 'The review changed or is busy. Reload before editing.'}, status=409)
        except (ValueError, TypeError, OverflowError):
            return Response({'detail': 'Check finite amounts, return assumptions and owned matching investments.'}, status=400)


class InvestmentImportConfirmAPI(InvestmentImportReviewAPI):
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        data = request.data
        if not isinstance(data, dict) or set(data) != {'confirm', 'token'} or data.get('confirm') is not True:
            return Response({'detail': 'Explicitly confirm the exact reviewed proposal.'}, status=400)
        try:
            document = get_object_or_404(InvestmentImportDocument, user=request.user, pk=pk)
            return Response(confirm_investment_review(document, token=data.get('token')))
        except (InvestmentReviewConflict, OperationalError):
            return Response({'detail': 'The review, source or holding changed, expired or is busy. Reopen it before confirming.'}, status=409)
        except (ValueError, TypeError):
            return Response({'detail': 'Check the reviewed fields; existing canonical investments were preserved.'}, status=400)
        except Http404:
            raise
        except Exception as exc:
            from alfred_ai.services.api_errors import safe_error_details
            return Response(safe_error_details(exc, 'Confirmation failed. The draft is preserved; reopen it and retry.',
                logger_name=__name__, field='detail'), status=500)


def _form_rows(preview):
    for row in preview['rows']:
        fields = []
        for name in FIELDS:
            value = row.get(name)
            if name in MONEY and value not in (None, ''):
                try: value = str(investment_money(value))
                except ValueError: pass
            choices = Investment.ASSET_TYPES if name == 'asset_type' else CURRENCY_CHOICES if name == 'currency' else []
            fields.append(dict(name=name, label=name.replace('_', ' ').capitalize(), value='' if value is None else str(value),
                original=row['original'].get(name), status=(row.get('field_status') or {}).get(name, 'missing').replace('_', ' '),
                choices=choices, kind='number' if name in (*MONEY, 'annual_return_rate') else 'text'))
        row['form_fields'] = fields


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def investment_import_review_view(request, pk):
    document = get_object_or_404(InvestmentImportDocument, user=request.user, pk=pk)
    error, status, preview = '', 200, None
    try:
        page = int(request.POST.get('page', request.GET.get('page', '1')))
        preview = investment_preview(document, page=page)
        _form_rows(preview)
    except (ValueError, TypeError):
        error, status = 'No current review is available. Retry the retained original in Documents.', 409
    if request.method == 'POST' and preview:
        try:
            edits = []
            for row in preview['rows']:
                edit = {'index': row['index']}
                for field in row['form_fields']:
                    value = request.POST.get(f"row-{row['index']}-{field['name']}", '')
                    if request.POST.get('action') == 'save' or value != field['value']:
                        edit[field['name']] = value
                action = request.POST.get(f"row-{row['index']}-action", '')
                target = request.POST.get(f"row-{row['index']}-target_id", '')
                target = int(target) if target else None
                if action != row['action']: edit['action'] = action
                if target != row.get('target_id'): edit['target_id'] = target
                if len(edit) > 1: edits.append(edit)
            if request.POST.get('action') == 'confirm' and not edits:
                if request.POST.get('reviewed') != 'yes': raise ValueError()
                confirm_investment_review(document, token=request.POST.get('token'))
            else:
                edit_investment_review(document, revision=int(request.POST.get('revision', '-1')), edits=edits)
            return redirect(f'/investments/import-uploads/{pk}/review/?page={page}')
        except (InvestmentReviewConflict, OperationalError):
            error, status = 'The review or holding changed. Your form input is preserved; reload and review current values.', 409
        except (ValueError, TypeError, OverflowError):
            error, status = 'Check the entered values and review checkbox. Save corrections before confirming.', 400
        for row in preview['rows']:
            for field in row['form_fields']:
                field['value'] = request.POST.get(f"row-{row['index']}-{field['name']}", field['value'])
        preview['can_confirm'] = False
    choices = list(Investment.objects.filter(user=request.user).order_by('pk').values('id', 'asset_name', 'account_number')[:200])
    return render(request, 'investments/import_review.html', {'document': document, 'preview': preview, 'review_error': error,
                                                      'investment_choices': choices}, status=status)
