from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from .models import BehavioralSignal
from .serializers import BehavioralSignalSerializer

class BehavioralSignalListCreateView(ListCreateAPIView):
    serializer_class = BehavioralSignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BehavioralSignal.objects.filter(user=self.request.user).order_by("-timestamp", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def behavioral_fingerprint(request):
    """Get user's behavioral fingerprint."""
    try:
        # Get last 30 days of signals
        thirty_days_ago = timezone.now() - timedelta(days=30)
        signals = BehavioralSignal.objects.filter(
            user=request.user,
            timestamp__gte=thirty_days_ago
        )

        if not signals.exists():
            return Response({
                "fingerprint": "No data",
                "stress_level": 0,
                "spending_pattern": "Pattern unavailable",
                "decision_style": "Style unavailable",
                "message": "Not enough behavioral data. Continue using Alfred to build your profile.",
                "insights": ["Capture a few days of stress, sleep, and work data to build your behavioral fingerprint."],
            })

        # Calculate behavioral metrics
        avg_stress = signals.aggregate(avg=Avg('stress_score'))['avg'] or 0
        avg_sleep = signals.aggregate(avg=Avg('sleep_hours'))['avg'] or 0
        avg_work = signals.aggregate(avg=Avg('work_hours'))['avg'] or 0

        if avg_stress >= 7 or avg_sleep < 5.5:
            fingerprint = "Overloaded"
            decision_style = "Reactive"
            spending_pattern = "Stress-sensitive"
        elif avg_stress <= 4 and avg_sleep >= 7:
            fingerprint = "Steady"
            decision_style = "Analytical"
            spending_pattern = "Controlled"
        else:
            fingerprint = "Adaptive"
            decision_style = "Balanced"
            spending_pattern = "Moderate"

        insights = []
        if avg_sleep < 6:
            insights.append("Sleep recovery is low. Watch for impulse decisions on tired days.")
        if avg_work > 10:
            insights.append("Work hours are elevated. Decision fatigue risk is likely rising.")
        if avg_stress >= 7:
            insights.append("Stress is consistently high. Delay non-essential spending or large commitments.")
        if not insights:
            insights.append("Current behavioral pattern looks stable and manageable.")

        return Response({
            "fingerprint": fingerprint,
            "stress_level": round(avg_stress, 2),
            "spending_pattern": spending_pattern,
            "decision_style": decision_style,
            "message": f"Average sleep is {avg_sleep:.1f}h and work hours are {avg_work:.1f}h.",
            "insights": insights[:4],
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def behavioral_stress(request):
    """Get stress analysis."""
    try:
        # Get last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        signals = BehavioralSignal.objects.filter(
            user=request.user,
            timestamp__gte=week_ago
        ).order_by('-timestamp')

        if not signals.exists():
            return Response({
                "current_stress": 0,
                "average_stress": 0,
                "trend": "Unknown",
                "weekly_data": [],
                "message": "No stress data available",
                "recommendations": ["Log a few behavioral snapshots to activate the stress advisor."],
            })

        # Calculate stress metrics
        recent_stress = list(signals.values_list('stress_score', flat=True)[:7])
        avg_stress = sum(recent_stress) / len(recent_stress) if recent_stress else 0

        # Determine trend
        if len(recent_stress) >= 4:
            midpoint = len(recent_stress) // 2
            recent_window = sum(recent_stress[:midpoint]) / midpoint
            older_window = sum(recent_stress[midpoint:]) / max(len(recent_stress[midpoint:]), 1)
            delta = recent_window - older_window
            if delta >= 0.6:
                trend = "Increasing"
            elif delta <= -0.6:
                trend = "Decreasing"
            else:
                trend = "Stable"
        elif len(recent_stress) >= 2:
            trend = "Increasing" if recent_stress[0] - recent_stress[-1] >= 0.5 else ("Decreasing" if recent_stress[-1] - recent_stress[0] >= 0.5 else "Stable")
        else:
            trend = "Stable"

        recommendations = []
        avg_sleep = signals.aggregate(avg=Avg('sleep_hours'))['avg'] or 0
        avg_work = signals.aggregate(avg=Avg('work_hours'))['avg'] or 0
        if avg_stress > 6:
            recommendations.append("Delay non-essential decisions during high-stress periods.")
        if avg_sleep < 6:
            recommendations.append("Low sleep is showing up in your behavioral baseline. Prioritize recovery.")
        if avg_work > 10:
            recommendations.append("Workload is heavy. Protect one low-pressure review window for finances.")
        if not recommendations:
            recommendations.append("Stress levels are healthy. Stay consistent with the current routine.")

        return Response({
            "current_stress": round(recent_stress[0] if recent_stress else 0, 2),
            "average_stress": round(avg_stress, 2),
            "trend": trend,
            "weekly_data": recent_stress[:7],
            "message": f"Average sleep {avg_sleep:.1f}h | average work hours {avg_work:.1f}h.",
            "recommendations": recommendations,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)
