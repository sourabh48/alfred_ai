"""Owner-only read APIs; financial evidence never accepts mutations."""
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from .memory import MemoryAPI
from ..services.canonical_evidence import choices, record_source, document_page, document_record_page


class FinancialEvidenceAPI(MemoryAPI):
    def get(self, request, kind=None, identity=None):
        return Response({'records':choices(request.user)} if kind is None else record_source(request.user,kind,identity))


class FinancialSourcePageAPI(MemoryAPI):
    def get(self, request, kind, identity):
        if set(request.query_params)-{'cursor'} or len(request.query_params.getlist('cursor'))>1: raise ValueError('Invalid source page.')
        return Response(document_page(request.user,kind,identity,cursor=request.query_params.get('cursor')))


class DocumentRecordPageAPI(MemoryAPI):
    def get(self, request, kind, document_id=None):
        if set(request.query_params)-{'cursor'} or len(request.query_params.getlist('cursor'))>1: raise ValueError('Invalid document discovery page.')
        return Response(document_record_page(request.user,kind,document_id,cursor=request.query_params.get('cursor')))

    def post(self, request, kind, document_id=None):
        # Search terms stay out of URLs/access logs; this POST never mutates evidence.
        if document_id is not None: raise MethodNotAllowed('POST')
        if request.query_params: raise ValueError('Document filters belong in the request body.')
        data=self.payload(('name','date_from','date_to','cursor'))
        return Response(document_record_page(request.user,kind,cursor=data.get('cursor'),
            filters={key:value for key,value in data.items() if key!='cursor'}))


class ClosureEvidenceAPI(MemoryAPI):
    def get(self, request, identity):
        from ..services.hybrid_intelligence import source_context
        from django.http import Http404
        try: source=source_context(request.user,'documents',document_id=identity)[0]
        except PermissionError as exc: raise Http404 from exc
        return Response(source)
