"""Private manual recovery review; no model or provider execution."""
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.services.api_errors import safe_error_response
from alfred_ai.services.api_parsing import TextJSONParser
from apps.ml_engine.api.conversations import current_session
from apps.ml_engine.services.conversation_history import ConversationPermission
from .services import history_review as review


@method_decorator(never_cache, name='dispatch')
class CareerHistoryReviewAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [TextJSONParser]

    def handle_exception(self, exc):
        if isinstance(exc, ConversationPermission):
            return Response({'detail':'Sign in again before reviewing private history.'}, status=403)
        if isinstance(exc, review.ActionError):
            return Response({'detail':str(exc)}, status=409 if isinstance(exc, review.ActionConflict) else 400)
        if isinstance(exc, (Http404, APIException)):
            return super().handle_exception(exc)
        return safe_error_response(exc, 'The review could not finish. Retry the same card safely or reload Career.',
            logger_name=__name__, status_code=503)

    def get(self, request, pk):
        if request.query_params:
            raise review.ActionError('This private review accepts no query parameters.')
        current_session(request)
        result = review.inspect(request.user, pk)
        current_session(request)
        return Response(result)

    def post(self, request, pk):
        if len(request.body)>4096 or not isinstance(request.data, dict):
            raise review.ActionError('Use a bounded history review request.')
        current_session(request)
        data = request.data
        mode = data.get('mode')
        allowed = {'preview':{'mode','revision','fields'}, 'confirm':{'mode','proposal_id','fields','confirmed'},
                   'cancel':{'mode','proposal_id'}}
        if not isinstance(mode, str) or mode not in allowed or set(data)!=allowed[mode]:
            raise review.ActionError('Use only the declared history review fields.')
        if mode=='preview':
            result = review.prepare(request.user, pk, data['revision'], data['fields'])
        elif mode=='confirm':
            result = review.confirm(request.user, pk, data['proposal_id'], data['fields'], data['confirmed'])
        else:
            result = review.cancel(request.user, pk, data['proposal_id'])
        current_session(request)
        return Response(result)
