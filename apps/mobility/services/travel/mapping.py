"""GeoJSON map contract shared by any browser renderer; no map API keys here."""
import os


def map_features(destination):
    features = []

    def point(name, kind, lat, lon, freshness="UNKNOWN", **extra):
        if lat is not None and lon is not None:
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"name": name, "kind": kind, "freshness": freshness, **extra}})

    point(destination["name"], "overnight", destination.get("lat"), destination.get("lon"), destination.get("source_freshness","STATIC_REFERENCE"), source_url=destination.get("source",""),expires_at=destination.get("discovery_result",{}).get("expires_at"))
    route = destination.get("route_result", {})
    for index, item in enumerate(route.get("payload", {}).get("routes", [])):
        if not item.get("geometry"):  # Google fallback routes carry no line for a non-Google map
            continue
        features.append({"type": "Feature", "geometry": item["geometry"],
            "properties": {"name": f"Route {index+1}", "kind": "route", "selected": bool(item.get("route_id") and item["route_id"] == destination.get("selected_route_id")), "freshness": route.get("freshness", "UNKNOWN"), "expires_at":route.get("expires_at")}})
    if destination.get("origin_location"):
        origin = destination["origin_location"]
        point(origin["name"],"origin",origin["lat"],origin["lon"],origin.get("freshness","STATIC_REFERENCE"))
    for result_key in ("places_result", "hotels_result", "stays_guide_result"):
        result = destination.get(result_key, {})
        for item in result.get("payload", {}).get("places", result.get("payload", {}).get("options", [])):
            point(item.get("name", "Place"), item.get("category", "hotel"), item.get("lat"), item.get("lon"), result.get("freshness", "UNKNOWN"), source_url=item.get("source_url", ""),expires_at=result.get("expires_at"))
    return {"type": "FeatureCollection", "features": features}


def map_configuration():
    # Google map tiles only (owner decision 2026-11-13). ALFRED fetches them itself, so the key never reaches the browser.
    # Country maps the owner downloaded in Settings show when Google tiles are missing or fail (offline).
    from .offline_maps import ATTRIBUTION, installed
    offline = {"offline_url": "/mobility/offline-tiles/{z}/{x}/{y}.mvt" if installed() else "", "offline_attribution": ATTRIBUTION}
    if not os.getenv("TRAVEL_GOOGLE_MAPS_API_KEY"):
        return {"provider": "google", "tile_url": "", "attribution": "", "attribution_url": "", **offline}
    return {"provider": "google", "tile_url": "/mobility/map-tiles/{z}/{x}/{y}.png", "attribution": "Map data © Google",
            "attribution_url": "https://www.google.com/intl/en_in/help/terms_maps/", **offline}
