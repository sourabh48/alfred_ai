"""Owner-only statement citations and explicit record confirmation."""
from rest_framework.response import Response

from alfred_ai.services.api_errors import safe_error_response
from apps.expenses.services.statement_evidence import evidence, review, choices, EvidenceConflict
from .memory import MemoryAPI


class StatementEvidenceAPI(MemoryAPI):
    def handle_exception(self, exc):
        if isinstance(exc, EvidenceConflict):
            return safe_error_response(exc, 'Statement evidence changed or requires source review. Reload before confirming.',
                logger_name=__name__, status_code=409)
        return super().handle_exception(exc)

    def get(self, request, identity=None):
        return Response(evidence(request.user, identity) if identity is not None else {'records':choices(request.user)})

    def post(self, request, identity):
        data = self.payload(('revision', 'confirm'))
        return Response(review(request.user, identity, revision=data.get('revision'), confirm=data.get('confirm')))

    def delete(self, request, identity):
        data = self.payload(('revision', 'confirm'))
        return Response(review(request.user, identity, revision=data.get('revision'), confirm=data.get('confirm'), revoke=True))
