from collections import defaultdict
from datetime import date

from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.portfolio_intelligence import portfolio_intelligence_service
from .models import Investment
from .serializers import InvestmentSerializer


class InvestmentListCreateView(ListCreateAPIView):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user).order_by("-current_value", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InvestmentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Investment.objects.filter(user=self.request.user)


class InvestmentSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        investments = list(Investment.objects.filter(user=request.user).order_by("-current_value", "-id"))
        total_value = sum(item.current_value for item in investments)
        total_invested = sum(item.invested_amount for item in investments)
        total_sip = sum(item.monthly_sip for item in investments)
        weighted_return = (
            sum(item.current_value * item.annual_return_rate for item in investments) / total_value if total_value else 0.0
        )
        gain_loss = total_value - total_invested
        analysis = portfolio_intelligence_service.analyze_portfolio_risk(request.user)

        return Response(
            {
                "summary": {
                    "total_value": round(total_value, 2),
                    "total_invested": round(total_invested, 2),
                    "monthly_sip": round(total_sip, 2),
                    "annual_return": round(weighted_return, 2),
                    "gain_loss": round(gain_loss, 2),
                    "risk": _portfolio_risk(investments),
                    "positions": len(investments),
                },
                "analysis": analysis,
                "positions": InvestmentSerializer(investments, many=True).data,
            }
        )


class InvestmentAllocationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        investments = list(Investment.objects.filter(user=request.user))
        buckets: dict[str, float] = defaultdict(float)
        labels = dict(Investment.ASSET_TYPES)

        for item in investments:
            buckets[item.asset_type] += item.current_value

        ordered = sorted(buckets.items(), key=lambda pair: pair[1], reverse=True)
        return Response(
            {
                "labels": [labels.get(key, key.replace("_", " ").title()) for key, _ in ordered],
                "values": [round(value, 2) for _, value in ordered],
            }
        )


class InvestmentGrowthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        investments = list(Investment.objects.filter(user=request.user))
        today = date.today().replace(day=1)
        labels = []
        values = []

        for month_index in range(12):
            target_year = today.year + ((today.month - 1 + month_index) // 12)
            target_month = ((today.month - 1 + month_index) % 12) + 1
            labels.append(date(target_year, target_month, 1).strftime("%b %Y"))
            projected_value = 0.0
            for item in investments:
                projected_value += _project_position_value(
                    current_value=item.current_value,
                    monthly_sip=item.monthly_sip,
                    annual_return_rate=item.annual_return_rate,
                    months=month_index,
                )
            values.append(round(projected_value, 2))

        return Response({"labels": labels, "values": values})


def _portfolio_risk(investments: list[Investment]) -> str:
    if not investments:
        return "No data"

    total_value = sum(item.current_value for item in investments) or 1.0
    high_risk_weight = sum(
        item.current_value
        for item in investments
        if item.asset_type in {"equity", "crypto", "reit"} or item.risk_level.lower() == "high"
    )
    ratio = high_risk_weight / total_value
    if ratio >= 0.65:
        return "High"
    if ratio >= 0.35:
        return "Moderate"
    return "Conservative"


def _project_position_value(*, current_value: float, monthly_sip: float, annual_return_rate: float, months: int) -> float:
    value = float(current_value or 0)
    monthly_rate = float(annual_return_rate or 0) / 1200
    for _ in range(months + 1):
        value = (value + float(monthly_sip or 0)) * (1 + monthly_rate)
    return value
