"""Metadata only; callers cannot register tools or request arbitrary execution."""
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.assistant_tools import tool_catalog


@method_decorator(never_cache, name='dispatch')
class AssistantToolCatalogAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.query_params:
            return Response({'detail': 'This catalogue accepts no source or owner parameters.'}, status=400)
        return Response({'tools': tool_catalog()})
