from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum
from .models import Dependent
from .serializers import DependentSerializer

class DependentListCreateView(ListCreateAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class DependentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def family_growth(request):
    """Get family net-worth growth projection."""
    try:
        dependents = Dependent.objects.filter(user=request.user)

        # Get user's financial data
        from apps.investments.models import Investment
        from apps.expenses.models import BankAccount
        from apps.loans.models import Loan

        # Calculate current net worth
        total_investments = Investment.objects.filter(user=request.user).aggregate(
            total=Sum('current_value')
        )['total'] or 0

        total_cash = BankAccount.objects.filter(user=request.user, is_active=True).aggregate(
            total=Sum('current_balance')
        )['total'] or 0

        total_debt = Loan.objects.filter(user=request.user, is_active=True).aggregate(
            total=Sum('remaining_balance')
        )['total'] or 0

        current_net_worth = total_investments + total_cash - total_debt

        # Project growth (simple 8% annual growth assumption)
        projections = []
        for year in range(1, 11):  # 10-year projection
            projected_value = current_net_worth * (1.08 ** year)
            projections.append({
                "year": year,
                "projected_net_worth": round(projected_value, 2),
            })

        return Response({
            "current_net_worth": round(current_net_worth, 2),
            "dependents_count": dependents.count(),
            "growth_rate": 8.0,  # Assumed 8% annual growth
            "projections": projections,
            "insights": [
                f"Current family net worth: INR {current_net_worth:,.0f}",
                f"Supporting {dependents.count()} dependents",
                "Consider increasing SIP investments for faster growth",
                "Emergency fund should cover 6 months of expenses"
            ]
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)
