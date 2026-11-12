"""WEALTH2-001 API: owner-uploaded fund portfolio files, read once in memory; nothing is stored."""
from django.utils import timezone
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.services.upload_limits import UploadFormatError, UploadLimitExceeded, read_upload_bytes
from .services.fund_look_through import MAX_FILES, LookThroughError, look_through


class FundLookThroughView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        files, ids = request.FILES.getlist("file"), request.data.getlist("investment")
        if not files or len(files) != len(ids) or len(files) > MAX_FILES or set(request.FILES) - {"file"}:
            return Response({"detail": f"Upload one portfolio file per chosen fund (up to {MAX_FILES})."}, status=400)
        if not all(str(value).isdigit() for value in ids):
            return Response({"detail": "Choose one of your own holdings for each file."}, status=400)
        try:
            uploads = [(int(identity), read_upload_bytes(upload), upload.name) for identity, upload in zip(ids, files)]
            result = look_through(request.user, uploads, today=timezone.localdate())
        except LookThroughError as error:
            return Response({"detail": str(error)}, status=400)
        except (UploadFormatError, UploadLimitExceeded) as error:
            return Response({"detail": str(error.detail)}, status=error.status_code)
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response
