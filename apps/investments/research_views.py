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
from alfred_ai.services import public_http
from alfred_ai.services.currency import CURRENCY_CHOICES
from .models import ResearchDecision
from .services.research_journal import lessons, outcome, thesis_history

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


class ResearchHistoryView(APIView):
    """Each instrument's views as versions, newest first; reading it changes nothing."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"instruments": thesis_history(request.user, today=timezone.localdate())})


class ResearchLessonsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(lessons(request.user, str(request.query_params.get("instrument") or "")[:120]))


def _packet(user, params):
    """(packet, None) or (None, error Response); the holding is always the owner's own."""
    from django.db.models import Sum
    from .models import Investment
    from .services.research_packet import research_packet

    holding, total, raw = None, None, str(params.get("holding") or "")
    if raw:
        if not raw.isdigit() or len(raw) > 18:
            return None, Response({"detail": "Choose one of your holdings."}, status=status.HTTP_400_BAD_REQUEST)
        holding = get_object_or_404(Investment, pk=int(raw), user=user)
        same = Investment.objects.filter(user=user)
        same = same.in_rupee_totals() if holding.currency in (None, "INR") else same.filter(currency=holding.currency)
        total = same.aggregate(total=Sum("current_value"))["total"] or None
    try:
        return research_packet(str(params.get("symbol") or ""), holding=holding, portfolio_total=total), None
    except ValueError as exc:
        from .services.research_packet import find_symbols
        try:
            matches = find_symbols(params.get("symbol"))  # a newcomer may type "Infosys" rather than INFY.NS
        except (public_http.PublicHTTPError, ValueError, KeyError, TypeError, AttributeError):
            matches = []
        if matches:
            return None, Response({"detail": "Which company did you mean? Choose one below.", "code": "choose_symbol", "matches": matches},
                                  status=status.HTTP_400_BAD_REQUEST)
        return None, Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except public_http.PublicHTTPError as exc:
        return None, Response({"detail": f"Yahoo data is unavailable right now ({exc.code}). Try again later."}, status=status.HTTP_502_BAD_GATEWAY)


class ResearchPacketView(APIView):
    """INVEST2-001: owner-requested evidence packet for one symbol; reads public data, writes nothing."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        packet, error = _packet(request.user, request.query_params)
        return error or Response(packet)


class ResearchChallengeView(APIView):
    """INVEST2-001: the local model questions the packet the server rebuilds; client text is never forwarded."""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        from .services.research_challenge import challenge_packet

        from .services.research_challenge import ROLES

        data = request.data if isinstance(request.data, dict) else {}
        role = data.get("role") or "sceptic"
        if role not in ROLES:
            return Response({"detail": "Choose the sceptic, advocate or risk manager."}, status=status.HTTP_400_BAD_REQUEST)
        packet, error = _packet(request.user, data)
        if error:
            return error
        try:
            return Response(challenge_packet(packet, role=role))
        except (EmbeddingUnavailable, ValueError):
            return Response({"detail": "The local model could not challenge this packet. Check that Ollama is running and try again."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ResearchPersonalChallengeView(APIView):
    """WEALTH2-004: the local model challenges the owner's own view and position; only with consent for this request."""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        from .services.research_challenge import personal_challenge

        data = request.data if isinstance(request.data, dict) else {}
        if data.get("include_personal") is not True:
            return Response({"detail": "Tick that ALFRED may use your holding and saved views for this check."}, status=status.HTTP_400_BAD_REQUEST)
        packet, error = _packet(request.user, data)
        if error:
            return error
        try:
            return Response(personal_challenge(request.user, packet, today=timezone.localdate()))
        except (EmbeddingUnavailable, ValueError):
            return Response({"detail": "The local model could not challenge your view. Check that Ollama is running and try again."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
