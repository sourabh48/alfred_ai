"""INVEST2-002 research journal API: owner calls separate from holdings, settled with owner-entered prices."""
from datetime import date
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.services.api_parsing import TextJSONParser as JSONParser
from alfred_ai.services.currency import CURRENCY_CHOICES
from .models import ResearchDecision
from .services.research_journal import lessons, outcome

PRICE = dict(max_digits=18, decimal_places=4, min_value=Decimal("0.0001"))


class ResearchDecisionSerializer(serializers.ModelSerializer):
    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)
    entry_price = serializers.DecimalField(**PRICE)
    benchmark_entry = serializers.DecimalField(**PRICE, required=False, allow_null=True)
    outcome = serializers.SerializerMethodField()

    class Meta:
        model = ResearchDecision
        fields = ("id", "instrument", "rating", "thesis", "decided_on", "review_on", "currency", "entry_price", "benchmark",
                  "benchmark_entry", "settled_on", "exit_price", "benchmark_exit", "lesson", "outcome", "created_at", "updated_at")
        read_only_fields = ("settled_on", "exit_price", "benchmark_exit", "lesson", "created_at", "updated_at")

    def get_outcome(self, obj):
        return outcome(obj)

    def validate_instrument(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name the instrument.")
        return value.strip()

    def validate_thesis(self, value):
        if not value.strip():
            raise serializers.ValidationError("Write the thesis behind the call.")
        return value.strip()

    def validate_currency(self, value):
        return value or None  # blank means not recorded, never a guessed INR

    def validate_decided_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("The decision date cannot be in the future.")
        return value

    def validate(self, attrs):
        if attrs["review_on"] <= attrs["decided_on"]:
            raise serializers.ValidationError({"review_on": "Review after the decision date."})
        if attrs.get("benchmark_entry") is not None and not (attrs.get("benchmark") or "").strip():
            raise serializers.ValidationError({"benchmark": "Name the benchmark whose level you entered."})
        return attrs


class ResearchDecisionListCreateView(ListCreateAPIView):
    serializer_class = ResearchDecisionSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get_queryset(self):
        return ResearchDecision.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ResearchDecisionDetailView(RetrieveDestroyAPIView):
    serializer_class = ResearchDecisionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ResearchDecision.objects.filter(user=self.request.user)


class SettlementSerializer(serializers.Serializer):
    settled_on = serializers.DateField(required=False)
    exit_price = serializers.DecimalField(**PRICE, required=False)
    benchmark_exit = serializers.DecimalField(**PRICE, required=False, allow_null=True)
    lesson = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class ResearchDecisionSettleView(APIView):
    """Settle once the review date has passed; afterwards only the lesson can change. Holdings are never touched."""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        decision = get_object_or_404(ResearchDecision, pk=pk, user=request.user)
        serializer = SettlementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data, today = serializer.validated_data, timezone.localdate()
        if decision.settled_on is not None:
            if set(data) != {"lesson"}:
                return Response({"detail": "This call is already settled; only its lesson can change."}, status=status.HTTP_400_BAD_REQUEST)
            decision.lesson = data["lesson"].strip()
            decision.save(update_fields=["lesson", "updated_at"])
            return Response(ResearchDecisionSerializer(decision).data)
        settled_on = data.get("settled_on") or today
        errors = {}
        if settled_on > today:
            errors["settled_on"] = "The settlement date cannot be in the future."
        elif settled_on < decision.review_on:
            errors["settled_on"] = f"Settle on or after the review date, {decision.review_on.isoformat()}."
        if data.get("exit_price") is None:
            errors["exit_price"] = "Enter the closing price you checked."
        if decision.benchmark_entry is not None and data.get("benchmark_exit") is None:
            errors["benchmark_exit"] = f"Enter the closing level of {decision.benchmark}."
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        decision.settled_on, decision.exit_price = settled_on, data["exit_price"]
        decision.benchmark_exit = data.get("benchmark_exit") if decision.benchmark_entry is not None else None
        decision.lesson = (data.get("lesson") or "").strip()
        decision.save(update_fields=["settled_on", "exit_price", "benchmark_exit", "lesson", "updated_at"])
        return Response(ResearchDecisionSerializer(decision).data)


class ResearchLessonsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(lessons(request.user, str(request.query_params.get("instrument") or "")[:120]))
