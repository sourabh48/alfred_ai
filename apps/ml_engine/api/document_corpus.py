"""Private document copies require explicit owner consent; canonical evidence is read-only."""
from io import BytesIO

from django.http import FileResponse
from rest_framework.response import Response

from .memory import MemoryAPI, memory_store
from ..services.document_corpus import DocumentCorpus


class DocumentCorpusAPI(MemoryAPI):
    def get(self, request):
        if request.query_params:
            raise ValueError('Document knowledge does not accept URL filters.')
        return Response(DocumentCorpus(memory_store()).list(request.user))

    def post(self, request):
        if request.query_params:
            raise ValueError('Document knowledge requests belong in the body.')
        data = self.payload(('kind', 'document_id', 'catalog_token', 'consent', 'days'))
        return Response(DocumentCorpus(memory_store()).ingest(request.user, data.get('kind'), data.get('document_id'),
            catalog_token=data.get('catalog_token'), consent=data.get('consent'), days=data.get('days')))


class DocumentCorpusSearchAPI(MemoryAPI):
    def post(self, request):
        if request.query_params:
            raise ValueError('Search keywords belong in the request body.')
        data = self.payload(('ids', 'query'))
        return Response(DocumentCorpus(memory_store()).search(request.user, data.get('ids'), data.get('query')))


class DocumentCorpusUploadAPI(MemoryAPI):
    def post(self, request):
        if request.query_params or request.content_type.split(';')[0] != 'multipart/form-data':
            raise ValueError('Use a private multipart upload with no URL fields.')
        data = self.payload(('file', 'consent', 'days'))
        if any(len(data.getlist(key)) != 1 for key in data) or set(data) != {'file', 'consent', 'days'}:
            raise ValueError('Choose one file, explicit consent and retention.')
        days = data.get('days', '')
        if not isinstance(days, str) or not days.isascii() or not days.isdecimal() or len(days) > 2:
            raise ValueError('Choose 1–30 days retention.')
        return Response(DocumentCorpus(memory_store()).upload(request.user, data['file'],
            consent=data['consent'] == 'true', days=int(days)))


class DocumentCorpusOriginalAPI(MemoryAPI):
    def get(self, request, identity):
        if request.query_params:
            raise ValueError('Choose only the private original.')
        source, raw = DocumentCorpus(memory_store()).original(request.user, identity)
        response = FileResponse(BytesIO(raw), as_attachment=True, filename=source['document_name'],
            content_type='application/pdf' if source['original_format'] == 'pdf' else 'text/plain; charset=utf-8')
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class DocumentCorpusDetailAPI(MemoryAPI):
    def delete(self, request, identity):
        if request.query_params or request.data:
            raise ValueError('Choose only the private document to remove.')
        DocumentCorpus(memory_store()).delete(request.user, identity)
        return Response({'deleted': True})
