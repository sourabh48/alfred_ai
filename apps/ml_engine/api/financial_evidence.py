"""Owner-only read APIs; financial evidence never accepts mutations."""
from rest_framework.response import Response
from .memory import MemoryAPI
from ..services.canonical_evidence import choices, record_source, document_page


class FinancialEvidenceAPI(MemoryAPI):
    def get(self, request, kind=None, identity=None):
        return Response({'records':choices(request.user)} if kind is None else record_source(request.user,kind,identity))


class FinancialSourcePageAPI(MemoryAPI):
    def get(self, request, kind, identity):
        if set(request.query_params)-{'cursor'} or len(request.query_params.getlist('cursor'))>1: raise ValueError('Invalid source page.')
        return Response(document_page(request.user,kind,identity,cursor=request.query_params.get('cursor')))


class ClosureEvidenceAPI(MemoryAPI):
    def get(self, request, identity):
        from ..services.hybrid_intelligence import source_context
        from django.http import Http404
        try: source=source_context(request.user,'documents',document_id=identity)[0]
        except PermissionError as exc: raise Http404 from exc
        return Response(source)
