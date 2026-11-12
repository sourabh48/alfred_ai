"""WEALTH2-001 API: owner-uploaded fund portfolio files, read in memory; parsed rows are saved only when asked."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.services.upload_limits import UploadFormatError, UploadLimitExceeded, read_upload_bytes
from .models import FundPortfolioSnapshot
from .services.fund_look_through import MAX_FILES, LookThroughChoice, LookThroughError, look_through, look_through_saved


def _private(data, status=200):
    response = Response(data, status=status)
    response["Cache-Control"] = "no-store"
    return response


class FundLookThroughView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        files, ids = request.FILES.getlist("file"), request.data.getlist("investment")
        if not files or len(files) != len(ids) or len(files) > MAX_FILES or set(request.FILES) - {"file"}:
            return Response({"detail": f"Upload one portfolio file per chosen fund (up to {MAX_FILES})."}, status=400)
        if not all(str(value).isdigit() for value in ids):
            return Response({"detail": "Choose one of your own holdings for each file."}, status=400)
        save = request.data.get("save") in ("1", "true")
        sheets = request.data.getlist("sheet")  # optional, one per file: the fund's sheet in a multi-fund workbook
        if sheets and (len(sheets) != len(files) or any(len(value) > 100 for value in sheets)):
            return Response({"detail": "Choose which fund in each file belongs to the holding."}, status=400)
        try:
            uploads = [(int(identity), read_upload_bytes(upload), upload.name) for identity, upload in zip(ids, files)]
            result = look_through(request.user, uploads, today=timezone.localdate(), save=save,
                                  sheets=[value or None for value in sheets] or None)
        except LookThroughChoice as choice:
            # Not an error: the page asks the owner which fund in the file to use, then posts again.
            return _private({"choose": {"file_index": choice.index, "funds": choice.funds}, "detail": str(choice)})
        except LookThroughError as error:
            return Response({"detail": str(error)}, status=400)
        except (UploadFormatError, UploadLimitExceeded) as error:
            return Response({"detail": str(error.detail)}, status=error.status_code)
        return _private(result)


class SavedFundPortfolioView(APIView):
    """GET lists the owner's saved portfolios; POST {"investment": [ids]} looks through the latest saved one of each."""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request):
        rows = FundPortfolioSnapshot.objects.filter(user=request.user).select_related("investment")
        return _private([{"id": row.pk, "investment_id": row.investment_id, "holding": row.investment.asset_name,
                          "scheme": row.scheme, "as_of": row.as_of.isoformat() if row.as_of else None,
                          "saved_at": row.uploaded_at.isoformat(), "securities": len(row.securities)} for row in rows])

    def post(self, request):
        ids = request.data.get("investment") if isinstance(request.data, dict) else None
        if not isinstance(ids, list) or not all(isinstance(value, int) and not isinstance(value, bool) for value in ids):
            return Response({"detail": "Choose one of your own holdings with a saved portfolio."}, status=400)
        try:
            return _private(look_through_saved(request.user, ids, today=timezone.localdate()))
        except LookThroughError as error:
            return Response({"detail": str(error)}, status=400)


class SavedFundPortfolioDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        get_object_or_404(FundPortfolioSnapshot, pk=pk, user=request.user).delete()
        return Response(status=204)
