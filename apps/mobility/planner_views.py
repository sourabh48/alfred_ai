from copy import deepcopy

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BikeProfile, TravelFeedback, TravelPlan, TravelPlanningSession, TripPhoto
from .serializers import TravelPlanSerializer
from .services.travel_conversation import STYLE_WORDS, new_session, save_plan, send_message
from .services.travel_discovery import fact, learn, profile_for, value
from .services.travel_research import STAGES, TERMINAL, evidence_payload, queue_research
from .services.travel.presentation import age_saved_facts
from .services.travel.mapping import map_configuration
from .services.travel.cache import usage_summary
from .services.travel.discovery import remember, place_key
from .services.travel.intent import PROFILE_KEYS, validate_preference


class PlannerWriteThrottle(UserRateThrottle):
    scope = "travel_planner"
    rate = "60/min"

    def allow_request(self, request, view):
        return True if request.method == "GET" else super().allow_request(request, view)


def session_payload(session):
    session.refresh_from_db()
    run = session.research_runs.first()
    candidates = deepcopy(session.candidates)
    now = timezone.now().isoformat()
    for candidate in candidates:
        for source in candidate.get("sources", []):
            if source.get("valid_until") and source["valid_until"] <= now:
                source["freshness"] = "CACHED"
                source["confidence"] = "UNKNOWN"
                if source["data_type"] == "weather":
                    candidate["weather"] = {"summary":"This forecast is stale. Recheck this trip for current information.","confidence":"UNKNOWN"}
                    candidate["factors"]["Weather"] = "Stale · recheck"
    itinerary = deepcopy(session.itinerary)
    if itinerary:
        for source in itinerary.get("sources", []):
            if source.get("valid_until") and source["valid_until"] <= now:
                source["freshness"] = "CACHED"
                source["confidence"] = "UNKNOWN"
                if source["data_type"] == "weather":
                    itinerary["weather"] = {"summary":"This forecast is stale. Recheck Trip before relying on it.","confidence":"UNKNOWN"}
    return age_saved_facts({"id": session.id, "title": session.title, "state": session.state, "status": session.status,
            "map_config":map_configuration(), "can_view_provider_usage":session.user.is_staff,
            "revision": session.revision, "plan_id": session.plan_id, "candidates": candidates, "itinerary": itinerary,
            "messages": list(session.messages.values("id", "role", "text", "chips", "created_at")),
            "research": ({"id": run.id, "status": run.status, "stage": STAGES.get(run.status, run.status),
                          "deep": run.deep, "summary": run.summary, "error": run.error, "changes": run.changes,
                          "sources_checked": run.sources_checked, "candidate_count": run.candidate_count,
                          "created_at": run.created_at, "completed_at": run.completed_at,
                          "evidence": [evidence_payload(e) for e in run.evidence.all()]} if run else None)})


class TravelSessionList(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PlannerWriteThrottle]

    def get(self, request):
        sessions = TravelPlanningSession.objects.filter(user=request.user)
        return Response({"sessions": list(sessions.values("id", "title", "status", "plan_id", "updated_at")[:100]),
                         "plans": TravelPlanSerializer(TravelPlan.objects.filter(user=request.user), many=True).data})

    def post(self, request):
        plan = None
        if request.data.get("plan_id"):
            plan = get_object_or_404(TravelPlan, pk=request.data["plan_id"], user=request.user)
            existing = TravelPlanningSession.objects.filter(plan=plan, user=request.user).first()
            if existing:
                # Refresh stale public evidence only for upcoming trips near departure.
                run = existing.research_runs.first()
                if plan.start_date and 0 <= (plan.start_date-timezone.localdate()).days <= 15 and run and run.evidence.filter(valid_until__lt=timezone.now()).exists():
                    queue_research(existing, recheck=True)
                return Response(session_payload(existing))
        return Response(session_payload(new_session(request.user, plan)), status=201)


class TravelSessionDetail(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PlannerWriteThrottle]

    def get(self, request, pk):
        session = get_object_or_404(TravelPlanningSession, pk=pk, user=request.user)
        return Response(session_payload(session))

    @transaction.atomic
    def post(self, request, pk):
        session = get_object_or_404(TravelPlanningSession.objects.select_for_update(), pk=pk, user=request.user)
        action = request.data.get("action", "message")
        if action == "message":
            session = send_message(pk, request.user, request.data.get("text", ""))
        elif action == "save":
            save_plan(session, draft=request.data.get("draft") is True)
        elif action == "vehicle":
            bike = get_object_or_404(BikeProfile, pk=request.data.get("vehicle_id"), user=request.user)
            session.state["vehicle_profile"] = fact(bike.id)
            session.revision += 1
            session.save()
            from .services.travel_conversation import vehicle_state
            vehicle_state(session)
            session.save()
        elif action == "reject":
            chosen = next((c for c in session.candidates if c["name"] == request.data.get("destination")), None)
            if not chosen:
                raise ValidationError("Choose one of this session's destinations.")
            remember(request.user,chosen,"rejected")
            # Rejection is tentative, not a permanent dislike of every activity there.
            learn(request.user, "destination:"+chosen["name"], False, "Rejected recommendation", .5)
            avoided = value(session.state, "must_avoid", [])
            session.state["must_avoid"] = fact(list(dict.fromkeys(avoided+[chosen["name"]])))
            session.revision += 1
            session.save()
            queue_research(session)
        elif action == "refresh":
            queue_research(session,recheck=True,force=request.data.get("force") is True)
        elif action == "place":
            places = list(session.candidates)
            for candidate in session.candidates:
                places.extend(candidate.get("places_result",{}).get("payload",{}).get("places",[]))
            chosen = next((p for p in places if place_key(p) == request.data.get("place_key")),None)
            if not chosen:
                raise ValidationError("Choose a place returned in this conversation.")
            remember(request.user,chosen,request.data.get("event"))
        elif action == "status":
            status = request.data.get("status")
            if status not in {"draft","planned","completed","cancelled"}:
                raise ValidationError("Choose a valid trip status.")
            if status in {"planned","completed"} and not session.plan_id:
                raise ValidationError("Save a planned trip before marking its status.")
            session.status = status
            session.save(update_fields=["status","updated_at"])
            if session.plan_id:
                session.plan.status = status
                session.plan.full_clean()
                session.plan.save(update_fields=["status","updated_at"])
            if status == "completed" and value(session.state,"selected_destination"):
                remember(request.user,{"name":value(session.state,"selected_destination")},"visited")
        else:
            raise ValidationError("Unknown planner action.")
        return Response(session_payload(session))


class TravelProviderUsage(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .services.travel.providers.geocoding import OpenMeteoGeocoding
        from .services.travel.providers.weather import OpenMeteoWeather
        from .services.travel.providers.routing import OpenRouteService
        from .services.travel.providers.places import OverpassPlaces
        from .services.travel.providers.accommodation import DuffelAccommodation
        from .services.travel.providers.transport import DuffelFlights, IndianRailProvider
        from .services.travel.providers.web import BraveSearch, SearXNGSearch, WikivoyageSearch, WikivoyageDestinations
        providers = [OpenMeteoGeocoding(),OpenMeteoWeather(),OpenRouteService(),OverpassPlaces(),
                     DuffelAccommodation(),DuffelFlights(),IndianRailProvider(),BraveSearch(),
                     SearXNGSearch(),WikivoyageSearch(),WikivoyageDestinations()]
        return Response({"usage":usage_summary(),"configuration":[{"provider":p.name,"category":p.category,
            "unavailable_reason":p.unavailable_reason(),"application_limits":p.limits} for p in providers]})


class TravelPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        p = profile_for(request.user)
        return Response({"preferences": p.preferences, "novelty": p.novelty,
                         "learning_enabled": p.learning_enabled, "media_learning_enabled": p.media_learning_enabled,
                         "reset_at": p.reset_at})

    def patch(self, request):
        p = profile_for(request.user)
        data = request.data
        if "novelty" in data:
            if data["novelty"] not in {"mostly_new", "balanced", "mostly_familiar"}:
                raise ValidationError("Choose mostly new, balanced or mostly familiar.")
            p.novelty = data["novelty"]
        for key in ("learning_enabled", "media_learning_enabled"):
            if key in data:
                if not isinstance(data[key], bool):
                    raise ValidationError(f"{key} must be true or false.")
                setattr(p, key, data[key])
        if data.get("action") == "reset":
            p.preferences = {k: v for k, v in p.preferences.items() if v.get("confirmed_by_user")}
            p.reset_at = timezone.now()
        if "key" in data:
            key = str(data["key"])
            if key not in STYLE_WORDS and key not in PROFILE_KEYS and key not in p.preferences and key not in {"typical_duration", "typical_spend", "preferred_transport", "preferred_stay", "daily_distance", "climate", "riding_hours", "time_of_day", "companions"}:
                raise ValidationError("Unknown travel preference.")
            if data.get("action") == "remove":
                # Explicit suppression prevents learning it back without user intent.
                p.preferences[key] = {**fact(False, "user_removed", True), "reasons": ["Removed by you"]}
            else:
                val = data.get("value")
                validate_preference(key,val)
                p.preferences[key] = {**fact(val, "settings", True), "reasons": ["Edited by you"]}
        p.save()
        return self.get(request)


class TravelFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = TravelPlan.objects.filter(user=request.user, end_date__lt=timezone.localdate()).exclude(status__in=["draft", "cancelled"]).filter(feedback__isnull=True)
        return Response({"due": list(plans.values("id", "title", "destination")[:20])})

    def post(self, request):
        plan = get_object_or_404(TravelPlan, pk=request.data.get("plan_id"), user=request.user)
        if not plan.end_date or plan.end_date >= timezone.localdate():
            raise ValidationError("Feedback is available after the trip ends.")
        rating = request.data.get("rating")
        if rating not in {"loved", "good", "okay", "disliked"}:
            raise ValidationError("Choose a trip rating.")
        liked, disliked = request.data.get("liked", []), request.data.get("disliked", [])
        allowed = set(STYLE_WORDS) | {"scenery", "ride", "stay", "weather", "activities", "crowds", "roads", "distance", "cost"}
        if any(not isinstance(tags, list) or len(tags) > 20 or any(t not in allowed for t in tags) for tags in (liked, disliked)):
            raise ValidationError("Choose valid feedback tags.")
        if set(liked) & set(disliked):
            raise ValidationError("Choose either liked or disliked for each topic.")
        TravelFeedback.objects.update_or_create(plan=plan, defaults={"rating": rating, "liked": liked, "disliked": disliked})
        for tag in liked:
            learn(request.user, tag, True, f"Trip feedback: {plan.title}", .9)
        for tag in disliked:
            learn(request.user, tag, False, f"Trip feedback: {plan.title}", .9)
        learn(request.user, "typical_duration", plan.duration_days, f"Completed trip: {plan.title}", .65)
        learn(request.user, "typical_spend", plan.budget, f"Completed trip budget: {plan.title}", .55)
        return Response({"saved": True})


def photo_matches(photo, plan):
    if not photo.taken_at or not plan.start_date or not plan.end_date or plan.id in photo.ignored_plan_ids:
        return False
    if not plan.start_date <= photo.taken_at.date() <= plan.end_date:
        return False
    from .services.travel_media import near_destination
    return bool(plan.destination and ((photo.location_name and plan.destination.lower() in photo.location_name.lower())
                                      or near_destination(photo, plan.destination)))


class TravelMediaSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = list(TravelPlan.objects.filter(user=request.user, end_date__lt=timezone.localdate()).exclude(status="cancelled"))
        suggestions = []
        for photo in TripPhoto.objects.filter(user=request.user, travel_plan=None)[:500]:
            for plan in plans:
                if photo_matches(photo, plan):
                    suggestions.append({"photo_id": photo.id, "plan_id": plan.id, "plan_title": plan.title,
                                        "caption": photo.caption, "location": photo.location_name,
                                        "photo_url": photo.image.url, "reason": "Date window and location metadata match; please review."})
        return Response({"suggestions": suggestions})

    @transaction.atomic
    def post(self, request):
        photo = get_object_or_404(TripPhoto.objects.select_for_update(), pk=request.data.get("photo_id"), user=request.user)
        plan = get_object_or_404(TravelPlan, pk=request.data.get("plan_id"), user=request.user)
        if photo.travel_plan_id or not photo_matches(photo, plan):
            raise ValidationError("This association is no longer suggested. Review the photo details.")
        if request.data.get("action") == "add":
            photo.travel_plan = plan
        elif request.data.get("action") == "ignore":
            photo.ignored_plan_ids = list(set(photo.ignored_plan_ids+[plan.id]))
        else:
            raise ValidationError("Choose add or ignore.")
        photo.save()
        return Response({"saved": True})
