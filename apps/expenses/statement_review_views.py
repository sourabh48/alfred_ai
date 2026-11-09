from django.db import OperationalError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StatementUpload
from .services.statement_review import (
    StatementReviewConflict, confirm_statement, edit_statement_preview, statement_preview,
)


class StatementPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        return response

    def get(self, request, pk):
        upload = get_object_or_404(StatementUpload, pk=pk, user=request.user)
        try:
            return Response(statement_preview(upload, page=int(request.query_params.get('page', '1'))))
        except (ValueError, TypeError):
            return Response({'detail': 'This preview is unavailable. Retry the source or reload its current review.'}, status=409)

    def patch(self, request, pk):
        upload = get_object_or_404(StatementUpload, pk=pk, user=request.user)
        data = request.data
        if not isinstance(data, dict) or set(data) - {'revision', 'edits', 'account_number'}:
            return Response({'detail': 'Choose supported preview corrections.'}, status=400)
        try:
            upload = edit_statement_preview(upload, revision=data.get('revision'), edits=data.get('edits', []),
                                            account_number=data.get('account_number'))
            return Response(statement_preview(upload))
        except (StatementReviewConflict, OperationalError):
            return Response({'detail': 'The preview changed or is busy. Reload it before correcting.'}, status=409)
        except (ValueError, TypeError):
            return Response({'detail': 'Check the row dates, finite amounts, debit/credit direction and account number.'}, status=400)


class StatementConfirmView(StatementPreviewView):
    http_method_names = ['post', 'options']

    def post(self, request, pk):
        upload = get_object_or_404(StatementUpload, pk=pk, user=request.user)
        data = request.data
        if not isinstance(data, dict) or set(data) != {'token', 'confirm'} or data.get('confirm') is not True:
            return Response({'detail': 'Review and explicitly confirm this exact preview.'}, status=400)
        try:
            return Response(confirm_statement(upload, token=data.get('token')))
        except (StatementReviewConflict, OperationalError):
            return Response({'detail': 'The confirmation expired, changed or is busy. Review the current preview.'}, status=409)
        except (ValueError, TypeError):
            return Response({'detail': 'A valid reviewed confirmation is required. Existing records are preserved.'}, status=400)
