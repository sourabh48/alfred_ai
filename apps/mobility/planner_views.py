from copy import deepcopy

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.throttling import UserRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BikeProfile, TravelFeedback, TravelPlan, TravelPlanningSession, TripPhoto
from .serializers import TravelPlanSerializer
from .services.travel_conversation import STYLE_WORDS, new_session, save_plan, say, send_message
from apps.expenses.money import money_float
from .services.travel_discovery import budget_for, fact, learn, profile_for, value
from .services.travel_research import STAGES, TERMINAL, evidence_payload, queue_research
from .services.travel.presentation import age_saved_facts
from .services.travel.restrictions import KIND, record_restriction, restriction_context
from .services.travel.mapping import map_configuration, map_features
from .services.travel.cache import usage_summary
from .services.travel.discovery import remember, place_key
from .services.travel.intent import PROFILE_KEYS, validate_preference
from .services.travel_itinerary import build_itinerary, build_multi_stop_itinerary, compare_stop_orders
from .services.travel.editor import apply_edit, editor_payload
from .services.travel.documents import document_links, update_documents


class PlannerWriteThrottle(UserRateThrottle):
    scope = "travel_planner"
    rate = "60/min"

    def allow_request(self, request, view):
        return True if request.method == "GET" else super().allow_request(request, view)


def session_payload(session):
    session.refresh_from_db()
    run = session.research_runs.first()
    outdated = bool(run and any(value(run.request, key) != value(session.state, key)
                    for key in ("available_start_date", "available_end_date", "trip_duration")))
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
    itinerary, editor = editor_payload(session)
    if itinerary:
        for source in itinerary.get("sources", []):
            if source.get("valid_until") and source["valid_until"] <= now:
                source["freshness"] = "CACHED"
                source["confidence"] = "UNKNOWN"
                if source["data_type"] == "weather":
                    itinerary["weather"] = {"summary":"This forecast is stale. Recheck Trip before relying on it.","confidence":"UNKNOWN"}
    offset = value(session.state, "_destination_offset", 0)
    pool_count = len(value(session.state, "_destination_pool", []))
    payload = age_saved_facts({"id": session.id, "title": session.title,
            "state": {key: val for key, val in session.state.items() if not key.startswith(("_destination_", "_itinerary_"))}, "status": session.status,
            "itinerary_stops": [s["name"] for s in value(session.state, "_itinerary_stops", [])],
            "destination_pool": {"total": pool_count, "offset": offset,
                "has_previous": offset > 0 and (not value(session.state, "selected_destination") or bool(value(session.state, "_itinerary_stops"))),
                "has_more": offset+3 < pool_count and (not value(session.state, "selected_destination") or bool(value(session.state, "_itinerary_stops")))},
            "map_config":map_configuration(), "can_view_provider_usage":session.user.is_staff,
            "revision": session.revision, "plan_id": session.plan_id, "candidates": candidates, "itinerary": itinerary,
            "itinerary_editor": editor, "trip_documents": document_links(session),
            "messages": list(session.messages.values("id", "role", "text", "chips", "created_at")),
            "research": ({"id": run.id, "status": run.status, "outdated": outdated,
                          "stage": "Recheck needed" if outdated else STAGES.get(run.status, run.status),
                          "deep": run.deep,
                          "summary": "Trip dates changed. Previous research applies to the earlier window; recheck weather and offers." if outdated else run.summary,
                          "error": "" if outdated else run.error, "changes": [] if outdated else run.changes,
                          "sources_checked": 0 if outdated else run.sources_checked, "candidate_count": run.candidate_count,
                          "created_at": run.created_at, "completed_at": None if outdated else run.completed_at,
                          "evidence": [] if outdated else [evidence_payload(e) for e in run.evidence.all()]} if run else None)})
    return restriction_context(session, payload)


class PrivateTravelSessionAPI(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [PlannerWriteThrottle]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response


class TravelSessionList(PrivateTravelSessionAPI):

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


class TravelSessionDetail(PrivateTravelSessionAPI):

    def get(self, request, pk):
        session = get_object_or_404(TravelPlanningSession, pk=pk, user=request.user)
        return Response(session_payload(session))

    @transaction.atomic
    def post(self, request, pk):
        session = get_object_or_404(TravelPlanningSession.objects.select_for_update(), pk=pk, user=request.user)
        action = request.data.get("action", "message")
        if action == "message":
            session = send_message(pk, request.user, request.data.get("text", ""))
        elif action == "itinerary_edit":
            apply_edit(session, request.data)
        elif action == "trip_documents":
            choices = update_documents(session, request.data)
            return Response({**session_payload(session), **({"document_choices": choices} if choices is not None else {})})
        elif action in ("restriction_review", "restriction_withdraw"):
            if type(request.data.get("revision")) is not int or request.data["revision"] != session.revision:
                return Response({"detail": "This trip changed. Reload before reviewing a route restriction."}, status=409)
            data = {k: v for k, v in request.data.items() if k not in ("action", "revision")}
            if action == "restriction_review":
                evidence = record_restriction(session, data)
                say(session, f"Saved your reviewed restriction reference #{evidence.pk}. Source authenticity and whole-route motorcycle legality remain unverified.")
            else:
                if set(data) != {"evidence_id"} or type(data["evidence_id"]) is not int or data["evidence_id"] < 1:
                    raise ValidationError({"detail": "Choose one of this conversation's reviewed references."})
                from .models import TravelResearchEvidence
                evidence = get_object_or_404(TravelResearchEvidence, pk=data["evidence_id"], research__session=session,
                    data_type=KIND, provider="owner_reviewed_reference")
                evidence.status = "withdrawn"
                evidence.save(update_fields=["status"])
                say(session, f"Withdrew your review of restriction reference #{evidence.pk}; the historical quotation and source are retained.")
            session.revision += 1
            session.save(update_fields=["revision", "updated_at"])
        elif action == "route_choice":
            if type(request.data.get("revision")) is not int or request.data["revision"] != session.revision:
                return Response({"detail": "This trip changed. Reload it before choosing a route."}, status=409)
            if len(value(session.state, "_itinerary_stops", [])) > 1:
                raise ValidationError("These routes start at home, not at the preceding stop. Multi-stop legs need separate verification.")
            index, route_id = request.data.get("candidate_index"), request.data.get("route_id")
            if type(index) is not int or not 0 <= index < len(session.candidates) or not isinstance(route_id, str):
                raise ValidationError("Choose a route shown for this conversation's destination.")
            candidate = session.candidates[index]
            result = candidate.get("route_result", {})
            route = next((r for r in result.get("payload", {}).get("routes", []) if r.get("route_id") == route_id), None)
            try:
                checked, expiry = (parse_datetime(str(result.get(k) or "")) for k in ("retrieved_at", "expires_at"))
            except (ValueError, TypeError, OverflowError):
                checked = expiry = None
            now = timezone.now()
            if (not route or not result.get("success") or result.get("stale") or not result.get("source_url")
                    or not checked or not expiry or not timezone.is_aware(checked) or not timezone.is_aware(expiry)
                    or not checked <= now < expiry):
                return Response({"detail": "This route changed or expired. Recheck the trip before choosing again."}, status=409)
            candidate.update(selected_route_id=route_id, route_choice_confirmed=True, route_choice_required=False,
                distance_km=route["distance_km"], travel_hours=route["duration_hours"],
                distance_basis="Selected provider geometry; duration is an estimate. Scenic quality, motorcycle legality, closures and corridor stops remain unverified.")
            candidate["budget"] = budget_for(session.state, candidate)
            candidate["map"] = map_features(candidate)
            candidate["sources"] = [s for s in candidate.get("sources", []) if s.get("data_type") != "budget"] + [{
                "data_type": "budget", "finding": candidate["budget"], "confidence": "ESTIMATED", "freshness": "ESTIMATED",
                "source_name": "ALFRED budget formulas; selected route allowance", "source_url": "", "retrieved_at": now.isoformat()}]
            candidate["factors"]["Budget"] = "Over target" if candidate["budget"]["over_budget"] else "Within estimate"
            candidate["route_alternatives_note"] = "Route choice updates the allowance, not the destination ranking. Stops, road access and scenic quality need separate verification."
            pool = value(session.state, "_destination_pool", [])
            if pool:
                session.state["_destination_pool"] = fact([deepcopy(candidate) if (c["name"], c.get("lat"), c.get("lon")) ==
                    (candidate["name"], candidate.get("lat"), candidate.get("lon")) else c for c in pool])
            if session.itinerary.get("destination") == candidate["name"]:
                session.itinerary = build_itinerary(session.state, candidate)
                if value(session.state, "_itinerary_stops", []):
                    session.state["_itinerary_stops"] = fact([deepcopy(candidate)])
            session.revision += 1
            session.save()
        elif action in ("itinerary_stops", "itinerary_order_preview"):
            revision = request.data.get("revision")
            if type(revision) is not int or revision != session.revision:
                return Response({"detail": "This trip changed. Reload it before editing stops."}, status=409)
            if action == "itinerary_order_preview":
                proposal = compare_stop_orders(session.state, value(session.state, "_itinerary_stops", []))
                return Response({**session_payload(session), "stop_order_proposal": proposal})
            names = request.data.get("stops")
            if (not isinstance(names, list) or len(names) > 5 or any(not isinstance(n, str) or not 1 <= len(n) <= 180 for n in names)
                    or len(set(names)) != len(names)):
                raise ValidationError("Choose up to five distinct destinations in order.")
            available = {s["name"]: s for s in value(session.state, "_itinerary_stops", [])+session.candidates}
            if any(n not in available for n in names):
                raise ValidationError("Add destinations shown in this conversation; arbitrary or other-account places are not accepted.")
            stops = [deepcopy(available[n]) for n in names]
            itinerary = (build_multi_stop_itinerary(session.state, stops) if len(stops) > 1 else
                         build_itinerary(session.state, stops[0]) if stops else {})
            session.state["_itinerary_stops"] = fact(stops)
            session.state.pop("requested_destination", None)
            session.state.pop("selected_location", None)
            if stops:
                session.state["selected_destination"] = fact(names[0])
            else:
                session.state.pop("selected_destination", None)
            session.itinerary = itinerary
            session.revision += 1
            session.status = "ready" if stops else "researched"
            session.save()
        elif action == "save":
            if (value(session.state, "_itinerary_editor", {}) or "_itinerary_documents" in session.state) and (type(request.data.get("revision")) is not int or request.data["revision"] != session.revision):
                return Response({"detail": "This trip changed. Reload before saving the edited itinerary."}, status=409)
            save_plan(session, draft=request.data.get("draft") is True)
        elif action == "vehicle":
            bike = get_object_or_404(BikeProfile, pk=request.data.get("vehicle_id"), user=request.user)
            session.state["vehicle_profile"] = fact(bike.id)
            session.revision += 1
            session.save()
            from .services.travel_conversation import vehicle_state
            vehicle_state(session)
            stops = value(session.state, "_itinerary_stops", [])
            if stops:
                session.itinerary = build_multi_stop_itinerary(session.state, stops) if len(stops) > 1 else build_itinerary(session.state, stops[0])
            session.save()
        elif action == "reject":
            if request.data.get("destination") in [s["name"] for s in value(session.state, "_itinerary_stops", [])]:
                raise ValidationError("Remove this destination from your ordered stops before rejecting it.")
            chosen = next((c for c in session.candidates if c["name"] == request.data.get("destination")), None)
            if not chosen:
                raise ValidationError("Choose one of this session's destinations.")
            remember(request.user,chosen,"rejected")
            # Rejection is tentative, not a permanent dislike of every activity there.
            learn(request.user, "destination:"+chosen["name"], False, "Rejected recommendation", .5)
            avoided = value(session.state, "must_avoid", [])
            session.state["must_avoid"] = fact(list(dict.fromkeys(avoided+[chosen["name"]])))
            session.state.pop("_destination_pool", None)
            session.state.pop("_destination_offset", None)
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
        learn(request.user, "typical_spend", money_float(plan.budget), f"Completed trip budget: {plan.title}", .55)
        return Response({"saved": True})


def photo_matches(photo, plan):
    if not photo.taken_at or not plan.start_date or not plan.end_date or plan.id in photo.ignored_plan_ids:
        return False
    taken_date = timezone.localtime(photo.taken_at).date() if timezone.is_aware(photo.taken_at) else photo.taken_at.date()
    if not plan.start_date <= taken_date <= plan.end_date:
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
