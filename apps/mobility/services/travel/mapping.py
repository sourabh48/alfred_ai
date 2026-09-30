"""GeoJSON map contract shared by any browser renderer; no map API keys here."""
import os
from alfred_ai.services.public_http import normalized_link


def map_features(destination):
    features = []

    def point(name, kind, lat, lon, freshness="UNKNOWN", **extra):
        if lat is not None and lon is not None:
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {"name": name, "kind": kind, "freshness": freshness, **extra}})

    point(destination["name"], "overnight", destination.get("lat"), destination.get("lon"), destination.get("source_freshness","STATIC_REFERENCE"), source_url=destination.get("source",""),expires_at=destination.get("discovery_result",{}).get("expires_at"))
    route = destination.get("route_result", {})
    for index, item in enumerate(route.get("payload", {}).get("routes", [])):
        features.append({"type": "Feature", "geometry": item["geometry"],
            "properties": {"name": f"Route {index+1}", "kind": "route", "freshness": route.get("freshness", "UNKNOWN"), "expires_at":route.get("expires_at")}})
    if destination.get("origin_location"):
        origin = destination["origin_location"]
        point(origin["name"],"origin",origin["lat"],origin["lon"],"STATIC_REFERENCE")
    for result_key in ("places_result", "hotels_result"):
        result = destination.get(result_key, {})
        for item in result.get("payload", {}).get("places", result.get("payload", {}).get("options", [])):
            point(item.get("name", "Place"), item.get("category", "hotel"), item.get("lat"), item.get("lon"), result.get("freshness", "UNKNOWN"), source_url=item.get("source_url", ""),expires_at=result.get("expires_at"))
    return {"type": "FeatureCollection", "features": features}


def map_configuration():
    # Only public browser settings. Never use a server API credential here.
    tiles = os.getenv("TRAVEL_MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    # Public browser URL only, with no credential query. Browser key integrations
    # need a separately reviewed provider implementation.
    if not normalized_link(tiles) or "?" in tiles or "#" in tiles:
        tiles = ""
    return {"provider": "openstreetmap", "tile_url":tiles,
        "attribution": "© OpenStreetMap contributors", "attribution_url": "https://www.openstreetmap.org/copyright"}
