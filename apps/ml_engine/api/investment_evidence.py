"""Owner-only field confirmation using the existing session/CSRF/error boundary."""
from rest_framework.response import Response
from apps.investments.services.document_evidence import evidence, review
from .statements import StatementEvidenceAPI


class InvestmentEvidenceAPI(StatementEvidenceAPI):
    conflict_message = 'Investment field evidence changed or requires review. Reload before confirming.'
    def get(self, request, document_id, identity):
        return Response(evidence(request.user,document_id,identity))

    def post(self, request, document_id, identity):
        return self._review(request,document_id,identity)

    def delete(self, request, document_id, identity):
        return self._review(request,document_id,identity,revoke=True)

    def _review(self, request, document_id, identity, *, revoke=False):
        data=self.payload(('revision','fields','confirm'))
        return Response(review(request.user,document_id,identity,revision=data.get('revision'),
            fields=data.get('fields'),confirm=data.get('confirm'),revoke=revoke))
