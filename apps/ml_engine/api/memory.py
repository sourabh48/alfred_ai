"""Session-owned local memory lifecycle; family grants never grant memory access."""
from pathlib import Path

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.services.api_errors import safe_error_response
from apps.ml_engine.services.persistent_memory import MemoryStore


def memory_store():
    return MemoryStore(Path(settings.ALFRED_MEMORY_DIR))


class MemoryAPI(APIView):
    permission_classes = [IsAuthenticated]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store, private'
        return response

    def handle_exception(self, exc):
        if isinstance(exc, (ValueError, PermissionError)):
            return safe_error_response(exc, 'Memory request is invalid or not permitted.', logger_name=__name__)
        # DRF authentication/CSRF/HTTP errors retain their status and handling.
        from rest_framework.exceptions import APIException
        from django.http import Http404
        from django.core.exceptions import PermissionDenied
        if isinstance(exc, (APIException, Http404, PermissionDenied)):
            return super().handle_exception(exc)
        return safe_error_response(exc, 'Private memory is unavailable. Existing data is preserved.', logger_name=__name__, status_code=503)

    def payload(self, allowed):
        if not isinstance(self.request.data, dict) or set(self.request.data) - set(allowed):
            raise ValueError()
        return self.request.data


class MemoryCollectionAPI(MemoryAPI):
    def get(self, request):
        store = memory_store()
        return Response({'memories': store.list_memories(request.user), 'retention_days': store.retention_days(request.user)})

    def post(self, request):
        data = self.payload(('content', 'provenance', 'sensitivity', 'verified'))
        identity = memory_store().save_verified(request.user, data.get('content'), data.get('provenance'),
            sensitivity=data.get('sensitivity', 'sensitive'), verified=data.get('verified', False))
        return Response({'id': identity}, status=201)


class MemoryDetailAPI(MemoryAPI):
    def delete(self, request, identity):
        if not memory_store().delete_memory(request.user, identity):
            return Response({'detail': 'Memory was not found.'}, status=404)
        return Response(status=204)


class MemoryRetentionAPI(MemoryAPI):
    def put(self, request):
        data = self.payload(('days',))
        deleted = memory_store().set_retention(request.user, data.get('days'))
        return Response({'retention_days': data['days'], 'expired': deleted})


class MemoryResetAPI(MemoryAPI):
    def post(self, request):
        if self.payload(('confirm',)).get('confirm') is not True:
            raise ValueError()
        return Response({'deleted': memory_store().reset_owner(request.user)})


class MemoryRestoreAPI(MemoryAPI):
    def post(self, request):
        self.payload(())
        return Response({'restored': memory_store().restore_owner(request.user)})


class MemoryRetrieveAPI(MemoryAPI):
    def post(self, request):
        data = self.payload(('query', 'limit'))
        query = data.get('query')
        if not isinstance(query, str) or not query.strip() or len(query.encode()) > 8192:
            raise ValueError()
        return Response({'memories': memory_store().retrieve(request.user, query, limit=data.get('limit', 3))})
