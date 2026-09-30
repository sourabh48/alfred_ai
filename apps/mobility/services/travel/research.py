"""Provider orchestration inside the existing durable travel research worker."""
from copy import deepcopy
from datetime import date, timedelta
from math import ceil

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..travel_catalog import CITIES, lookup
from ..travel_discovery import budget_for, history_for, value, candidates_for
from .cache import query, query_with_fallback
from .discovery import rank_places
from .mapping import map_features
from .providers.base import ProviderResult
from .providers.geocoding import OpenMeteoGeocoding
from .providers.routing import OpenRouteService
from .providers.weather import OpenMeteoWeather, replan_proposals
from .providers.places import OverpassPlaces
from .providers.permits import PermitProvider
from .providers.accommodation import DuffelAccommodation
from .providers.transport import DuffelFlights, IndianRailProvider
from .providers.web import WikivoyageDestinations, WikivoyageSearch, BraveSearch, SearXNGSearch
from .links import external_links


def discover_destinations(user, state, preliminary):
    origin = CITIES.get(str(value(state,"origin","")).casefold())
    if not origin and value(state,"origin"):
        located = query(OpenMeteoGeocoding(),{"name":value(state,"origin")})
        matches = located.payload.get("locations",[])
        if len(matches) == 1:
            origin = (matches[0]["lat"],matches[0]["lon"])
    result = ProviderResult("wikivoyage","destinations",error="unambiguous_origin_required")
    if origin:
        radius = min(600,max(50,int(value(state,"maximum_daily_driving",300))))
        styles = value(state,"preferred_trip_style",[])
        interest = next((word for style,word in [("camping","camping"),("trekking","hiking"),("beaches","beach"),("waterfalls","waterfall"),("historical places","heritage")] if style in styles),"")
        params = {"latitude":origin[0],"longitude":origin[1],"radius_km":radius,"interest":interest}
        result = query(WikivoyageDestinations(),params,force=value(state,"force_refresh",False))
        if result.success and not result.payload.get("destinations") and interest:
            result = query(WikivoyageDestinations(),{**params,"interest":""},force=value(state,"force_refresh",False))
    seeds = result.payload.get("destinations",[])
    # Apply the existing transparent budget/time/preference/history ranking.
    options = candidates_for(user,state,limit=20,destinations=seeds,origin_coordinates=origin) if seeds else []
    if options:
        for d in options:
            d["discovery_result"] = result.as_dict()
            d["source_freshness"] = result.freshness
            d["why"].append("Dynamically discovered in a community travel guide; current access remains unverified.")
        return options
    fallback = deepcopy(preliminary)
    for d in fallback:
        d["discovery_result"] = result.as_dict()
        d["issues"].append("Dynamic discovery unavailable or no suitable results; showing the offline seed catalog.")
    return fallback


def research_candidates(user, state, preliminary):
    requested = value(state,"requested_destination") or value(state,"selected_destination")
    if not requested:
        return discover_destinations(user,state,preliminary)
    existing = next((d for d in preliminary if d["name"].casefold() == requested.casefold()), None)
    if existing:
        return [existing]
    chosen = value(state,"selected_location",{})
    seed = chosen if chosen.get("name","").casefold() == requested.casefold() else lookup(requested)
    result = None
    locations = []
    if seed:
        locations = [seed]
    else:
        result = query(OpenMeteoGeocoding(), {"name": requested}, force=value(state,"force_refresh",False))
        locations = result.payload.get("locations", [])
    if not locations:
        locations = [{"name":requested,"lat":None,"lon":None}]
    options = []
    for location in locations[:3]:
        d = {**location, "name": location["name"], "requested_name":requested,
             "styles":location.get("styles",[]),"activities":location.get("activities",[]),
             "stay":location.get("stay", "Choose accommodation after checking current inventory"),
             "nightly":location.get("nightly",1500),"caution":"Confirm local access, opening and transport conditions.",
             "authority":location.get("authority","Local authority"),"source":location.get("source",""),
             "distance_km":None,"travel_hours":None,"distance_basis":"No verified route yet.",
             "score":70,"fit":"Requested destination","why":["You asked for this destination; select the matching location if names are ambiguous."],
             "novelty":"Not yet assessed","factors":{"Weather":"Unknown","Roads / restrictions":"Unverified"},
             "weather":{"summary":"Not checked","confidence":"UNKNOWN"},"issues":[],"sources":[]}
        if location.get("region") or location.get("country"):
            d["location_label"] = ", ".join(filter(None,[location["name"],location.get("region"),location.get("country")]))
        if result:
            d["geocoding_result"] = result.as_dict()
        d["budget"] = budget_for(state,d)
        options.append(d)
    return options


def weather_result(destination, state, *, force=False):
    start, end = value(state,"available_start_date"), value(state,"available_end_date")
    if not start or not end:
        return ProviderResult("open_meteo","weather",error="dates_required")
    if not timezone.localdate() <= date.fromisoformat(start) <= date.fromisoformat(end) <= timezone.localdate()+timedelta(days=15):
        return ProviderResult("open_meteo","weather",error="outside_forecast_window")
    return query(OpenMeteoWeather(),{"latitude":destination["lat"],"longitude":destination["lon"],"start_date":start,"end_date":end},force=force)


def enrich_candidate(user, state, destination):
    d = deepcopy(destination)
    force = value(state,"force_refresh",False)
    results = []
    for key in ("geocoding_result","discovery_result"):
        if d.get(key):
            results.append(ProviderResult(**d[key]))
    def attach(key,result):
        d[key] = result.as_dict()
        results.append(result)
    coords = d.get("lat") is not None and d.get("lon") is not None
    origin = CITIES.get(str(value(state,"origin","")).casefold())
    if not origin and value(state,"origin"):
        geocoded = query(OpenMeteoGeocoding(),{"name":value(state,"origin")},force=force)
        results.append(geocoded)
        matches = geocoded.payload.get("locations",[])
        if len(matches) == 1:
            origin = (matches[0]["lat"], matches[0]["lon"])
        elif matches:
            d["issues"].append("Starting city is ambiguous; include region/country before routing.")
    if coords and origin:
        d["origin_location"] = {"name":value(state,"origin"),"lat":origin[0],"lon":origin[1]}
        route = query(OpenRouteService(),{"start":[origin[1],origin[0]],"end":[d["lon"],d["lat"]],
            "mode":value(state,"transport_mode","mixed"),"avoid_expressways":value(state,"avoid_expressways",False),
            "avoid_tolls":value(state,"avoid_tolls",False),"preference":value(state,"route_preference","recommended")},force=force)
        attach("route_result",route)
        if route.success:
            selected = route.payload["routes"][0]
            d.update(distance_km=selected["distance_km"],travel_hours=selected["duration_hours"],
                distance_basis="Provider-calculated route; duration is a model estimate, closures and motorcycle legality unverified.")
    else:
        attach("route_result",ProviderResult("openrouteservice","routing",error="unambiguous_origin_and_destination_coordinates_required"))
    try:
        weather = weather_result(d,state,force=force) if coords else ProviderResult("open_meteo","weather",error="destination_coordinates_required")
    except Exception:
        # An adapter fault must not discard the saved plan or other research.
        weather = ProviderResult("open_meteo","weather",error="weather_unavailable")
    attach("weather_result",weather)
    d["weather"] = {**weather.payload,"summary":weather.payload.get("summary","Current weather for these dates is unverified. Recheck nearer departure."),
                    "confidence":weather.confidence,"freshness":weather.freshness}
    d["weather_proposals"] = replan_proposals(weather)
    if d["weather_proposals"]:
        d["score"] -= 8
        d["factors"]["Weather"] = "Weather risks; review proposed changes"
    categories = ["attraction","camping","fuel","hospital","service"]
    if value(state,"find_restaurants"):
        categories.append("restaurant")
    places = query(OverpassPlaces(),{"latitude":d["lat"],"longitude":d["lon"],"categories":categories},force=force) if coords else ProviderResult("overpass","places",error="destination_coordinates_required")
    routes = d.get("route_result",{}).get("payload",{}).get("routes",[])
    route_points = (routes[0] if routes else {}).get("geometry",{}).get("coordinates",[])
    if places.success:
        history = history_for(user)
        places.payload["places"] = rank_places(user,places.payload["places"],interests=value(state,"preferred_trip_style",[]),
            route=route_points,visited_names=history["visits"],weather_risks=d["weather_proposals"],only_new=value(state,"only_new_places",False))
        d["activities"] = [p["name"] for p in places.payload["places"] if p["category"] not in {"fuel","hospital","service","restaurant","permit_office"}][:8] or d["activities"]
    attach("places_result",places)
    attach("permit_result",PermitProvider().lookup(value(state,"permit_place",d["name"]),start_date=value(state,"available_start_date")))
    start,end = value(state,"available_start_date"),value(state,"available_end_date")
    people = value(state,"number_of_travelers",1)
    hotel = query(DuffelAccommodation(),{"latitude":d["lat"],"longitude":d["lon"],"check_in":start,"check_out":end,"adults":people,"rooms":ceil(people/2)},force=force) if coords and start and end and start < end else ProviderResult("duffel","hotels",error="overnight_dates_and_destination_required")
    attach("hotels_result",hotel)
    flight = ProviderResult("duffel","flights",error="origin_and_destination_airport_codes_and_dates_required")
    if value(state,"origin_airport") and value(state,"destination_airport") and start:
        flight = query(DuffelFlights(),{"origin":value(state,"origin_airport"),"destination":value(state,"destination_airport"),
            "departure_date":start,"return_date":end,"adults":people},force=force)
    attach("flights_result",flight)
    attach("trains_result",query(IndianRailProvider(),{"origin":value(state,"origin"),"destination":d["name"],"date":start},force=force))
    attach("buses_result",ProviderResult("operator_links","buses",error="live_bus_inventory_not_configured",payload={"options":[],"availability":"UNKNOWN"}))
    # Search bounded, contextual topics; raw messages, budgets and history never leave.
    topics = ["closures"]
    requested_topics = value(state,"research_categories",[])
    for topic in ("permits","hotels","trains","flights","buses","camping","attractions","fuel","tolls"):
        if topic in requested_topics and topic not in topics:
            topics.append(topic)
    d["web_research"] = []
    for topic in topics[:3]:
        searched = query_with_fallback([BraveSearch(),SearXNGSearch(),WikivoyageSearch()],
            {"destination":value(state,"permit_place",d["name"]) if topic == "permits" else d["name"],
             "origin":value(state,"origin") if topic in {"closures","routing","trains","flights","buses"} else "",
             "topic":topic,"date":start,"mode":value(state,"transport_mode","mixed")},force=force)
        d["web_research"].append(searched.as_dict())
        results.append(searched)
    d["external_links"] = external_links(state,d)
    d["budget"] = budget_for(state,d)
    d["mode_comparison"] = [{"mode":mode,"budget":budget_for({**state,"transport_mode":{"value":mode}},d),
                             "availability":"UNKNOWN" if mode in {"train","flight"} else "Route legality and conditions unverified"}
                            for mode in value(state,"compare_modes",[])]
    d["map"] = map_features(d)
    d["quality"] = quality_contract(results)
    return d, results


def quality_contract(results):
    return {"verified":[r.category for r in results if r.success and not r.stale and r.status == "ok" and r.category not in {"web","destinations","permits"}],
            "research_leads":[r.category for r in results if r.success and r.category in {"web","destinations"}],
            "estimated":["budget", "travel duration", "local travel allowance"],
            "unavailable":[{"category":r.category,"reason":r.error or "unverified"} for r in results if not r.success or r.error],
            "freshness":[{"category":r.category,"freshness":r.freshness,"retrieved_at":r.retrieved_at,"expires_at":r.expires_at} for r in results],
            "recheck":["Weather and official warnings", "Road closures and vehicle legality", "Hotel/transport price and availability", "Permits, opening hours and entry requirements"]}
