"""Owner-only read APIs; financial evidence never accepts mutations."""
from rest_framework.response import Response
from .memory import MemoryAPI
from ..services.canonical_evidence import choices, record_source


class FinancialEvidenceAPI(MemoryAPI):
    def get(self, request, kind=None, identity=None):
        return Response({'records':choices(request.user)} if kind is None else record_source(request.user,kind,identity))
