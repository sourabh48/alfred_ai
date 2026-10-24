"""Private document copies require explicit owner consent; canonical evidence is read-only."""
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


class DocumentCorpusDetailAPI(MemoryAPI):
    def delete(self, request, identity):
        if request.query_params or request.data:
            raise ValueError('Choose only the private document to remove.')
        DocumentCorpus(memory_store()).delete(request.user, identity)
        return Response({'deleted': True})
