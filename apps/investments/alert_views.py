"""Authenticated local reminders share the existing encrypted owner vault."""
from rest_framework.response import Response

from apps.ml_engine.api.memory import MemoryAPI, memory_store
from .services.review_alerts import RecordReviewAlerts


class InvestmentReviewAlertView(MemoryAPI):
    def get(self, request):
        if request.query_params:
            raise ValueError('Reminder parameters belong in the request body.')
        return Response(RecordReviewAlerts(memory_store()).run(request.user))

    def post(self, request):
        if request.query_params:
            raise ValueError('Reminder parameters belong in the request body.')
        data=self.payload(('action','revision','enabled','days','consent','id'))
        return Response(RecordReviewAlerts(memory_store()).run(request.user,data))
