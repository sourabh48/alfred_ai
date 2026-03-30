from __future__ import annotations

from copy import deepcopy
from difflib import SequenceMatcher
import re


CLASS_DEFAULTS = {
    "hatchback": {"expected_mileage_kmpl": 19, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 90},
    "sedan": {"expected_mileage_kmpl": 18, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 95},
    "suv": {"expected_mileage_kmpl": 15, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 95},
    "mpv": {"expected_mileage_kmpl": 16, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 90},
    "commuter": {"expected_mileage_kmpl": 58, "service_interval_km": 4000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 55},
    "roadster": {"expected_mileage_kmpl": 42, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 70},
    "retro": {"expected_mileage_kmpl": 35, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 75},
    "adventure": {"expected_mileage_kmpl": 30, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 80},
    "sport": {"expected_mileage_kmpl": 35, "service_interval_km": 4500, "service_interval_days": 180, "optimal_cruising_speed_kmph": 85},
    "cruiser": {"expected_mileage_kmpl": 38, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 75},
    "touring": {"expected_mileage_kmpl": 30, "service_interval_km": 6000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 90},
    "scooter": {"expected_mileage_kmpl": 48, "service_interval_km": 3000, "service_interval_days": 150, "optimal_cruising_speed_kmph": 50},
    "custom": {"expected_mileage_kmpl": 35, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 65},
}


OFFICIAL_BIKE_CATALOG = [
    {
        "catalog_key": "royal-enfield-hunter-350",
        "vehicle_type": "motorcycle",
        "make": "Royal Enfield",
        "model_name": "Hunter 350",
        "variant": "",
        "display_name": "Royal Enfield Hunter 350",
        "bike_class": "retro",
        "engine_cc": 349.0,
        "fuel_tank_capacity_l": 13.0,
        "expected_mileage_kmpl": 36.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Royal Enfield",
        "official_source_url": "https://www.royalenfield.com/in/en/motorcycles/hunter-350/",
        "aliases": ["hunter 350", "re hunter", "royal enfield hunter"],
    },
    {
        "catalog_key": "royal-enfield-classic-350",
        "vehicle_type": "motorcycle",
        "make": "Royal Enfield",
        "model_name": "Classic 350",
        "variant": "",
        "display_name": "Royal Enfield Classic 350",
        "bike_class": "retro",
        "engine_cc": 349.0,
        "fuel_tank_capacity_l": 13.0,
        "expected_mileage_kmpl": 35.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Royal Enfield",
        "official_source_url": "https://www.royalenfield.com/in/en/motorcycles/classic-350/",
        "aliases": ["classic 350", "re classic", "royal enfield classic"],
    },
    {
        "catalog_key": "royal-enfield-meteor-350",
        "vehicle_type": "motorcycle",
        "make": "Royal Enfield",
        "model_name": "Meteor 350",
        "variant": "",
        "display_name": "Royal Enfield Meteor 350",
        "bike_class": "cruiser",
        "engine_cc": 349.0,
        "fuel_tank_capacity_l": 15.0,
        "expected_mileage_kmpl": 34.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Royal Enfield",
        "official_source_url": "https://www.royalenfield.com/in/en/motorcycles/meteor/",
        "aliases": ["meteor 350", "re meteor", "royal enfield meteor"],
    },
    {
        "catalog_key": "suzuki-v-strom-sx",
        "vehicle_type": "motorcycle",
        "make": "Suzuki",
        "model_name": "V-Strom SX",
        "variant": "",
        "display_name": "Suzuki V-Strom SX",
        "bike_class": "adventure",
        "engine_cc": 249.0,
        "fuel_tank_capacity_l": 12.0,
        "expected_mileage_kmpl": 36.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 85,
        "official_source_name": "Suzuki Motorcycle India",
        "official_source_url": "https://www.suzukimotorcycle.co.in/product-details/v-strom-sx",
        "aliases": ["v strom sx", "v-strom", "suzuki v strom"],
    },
    {
        "catalog_key": "bajaj-pulsar-n160",
        "vehicle_type": "motorcycle",
        "make": "Bajaj",
        "model_name": "Pulsar N160",
        "variant": "",
        "display_name": "Bajaj Pulsar N160",
        "bike_class": "roadster",
        "engine_cc": 164.82,
        "fuel_tank_capacity_l": 14.0,
        "expected_mileage_kmpl": 45.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Bajaj Auto",
        "official_source_url": "https://www.bajajauto.com/bikes/pulsar/pulsar-n160",
        "aliases": ["pulsar n160", "n160", "bajaj n160"],
    },
    {
        "catalog_key": "honda-sp125",
        "vehicle_type": "motorcycle",
        "make": "Honda",
        "model_name": "SP125",
        "variant": "",
        "display_name": "Honda SP125",
        "bike_class": "commuter",
        "engine_cc": 123.94,
        "fuel_tank_capacity_l": 11.2,
        "expected_mileage_kmpl": 60.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 60,
        "official_source_name": "Honda Motorcycle & Scooter India",
        "official_source_url": "https://www.honda2wheelersindia.com/SP125",
        "aliases": ["sp125", "sp 125", "honda sp125"],
    },
    {
        "catalog_key": "tvs-raider-125",
        "vehicle_type": "motorcycle",
        "make": "TVS",
        "model_name": "Raider 125",
        "variant": "",
        "display_name": "TVS Raider 125",
        "bike_class": "commuter",
        "engine_cc": 124.8,
        "fuel_tank_capacity_l": 10.0,
        "expected_mileage_kmpl": 57.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 60,
        "official_source_name": "TVS Motor",
        "official_source_url": "https://www.tvsmotor.com/tvs-raider",
        "aliases": ["raider 125", "tvs raider", "raider"],
    },
    {
        "catalog_key": "hero-splendor-plus",
        "vehicle_type": "motorcycle",
        "make": "Hero",
        "model_name": "Splendor Plus",
        "variant": "",
        "display_name": "Hero Splendor Plus",
        "bike_class": "commuter",
        "engine_cc": 97.2,
        "fuel_tank_capacity_l": 9.8,
        "expected_mileage_kmpl": 70.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 55,
        "official_source_name": "Hero MotoCorp",
        "official_source_url": "https://www.heromotocorp.com/content/dam/hero-commerce/in/en/products/practical/content-fragments/splendor-plus/assets/updated-image/Splendor%2BBrochure.pdf",
        "aliases": ["splendor", "splendor plus", "hero splendor"],
    },
    {
        "catalog_key": "hero-xpulse-200-4v",
        "vehicle_type": "motorcycle",
        "make": "Hero",
        "model_name": "Xpulse 200 4V",
        "variant": "",
        "display_name": "Hero Xpulse 200 4V",
        "bike_class": "adventure",
        "engine_cc": 199.6,
        "fuel_tank_capacity_l": 13.0,
        "expected_mileage_kmpl": 40.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 80,
        "official_source_name": "Hero MotoCorp",
        "official_source_url": "https://www.heromotocorp.com/en-in/motorcycles/xpulse-200-4v.html",
        "aliases": ["xpulse", "xpulse 200", "hero xpulse"],
    },
    {
        "catalog_key": "tvs-jupiter-110",
        "vehicle_type": "scooter",
        "make": "TVS",
        "model_name": "Jupiter 110",
        "variant": "",
        "display_name": "TVS Jupiter 110",
        "bike_class": "scooter",
        "engine_cc": 109.7,
        "fuel_tank_capacity_l": 6.0,
        "expected_mileage_kmpl": 50.0,
        "service_interval_km": 3000,
        "service_interval_days": 150,
        "optimal_cruising_speed_kmph": 50,
        "official_source_name": "TVS Motor",
        "official_source_url": "https://www.tvsmotor.com/en/ao/our-products/tvs-jupiter",
        "aliases": ["jupiter", "tvs jupiter", "jupiter 110"],
    },
    {
        "catalog_key": "maruti-suzuki-swift",
        "vehicle_type": "car",
        "make": "Maruti Suzuki",
        "model_name": "Swift",
        "variant": "",
        "display_name": "Maruti Suzuki Swift",
        "bike_class": "hatchback",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 37.0,
        "expected_mileage_kmpl": 24.8,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Maruti Suzuki India",
        "official_source_url": "https://www.marutisuzuki.com/swift",
        "aliases": ["swift", "maruti swift", "swift petrol"],
    },
    {
        "catalog_key": "maruti-suzuki-dzire",
        "vehicle_type": "car",
        "make": "Maruti Suzuki",
        "model_name": "Dzire",
        "variant": "",
        "display_name": "Maruti Suzuki Dzire",
        "bike_class": "sedan",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 37.0,
        "expected_mileage_kmpl": 24.8,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Maruti Suzuki India",
        "official_source_url": "https://www.marutisuzuki.com/dzire",
        "aliases": ["dzire", "maruti dzire", "swift dzire"],
    },
    {
        "catalog_key": "hyundai-creta",
        "vehicle_type": "car",
        "make": "Hyundai",
        "model_name": "Creta",
        "variant": "",
        "display_name": "Hyundai Creta",
        "bike_class": "suv",
        "engine_cc": 1497.0,
        "fuel_tank_capacity_l": 50.0,
        "expected_mileage_kmpl": 17.4,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Hyundai Motor India",
        "official_source_url": "https://www.hyundai.com/in/en/find-a-car/creta/highlights",
        "aliases": ["creta", "hyundai creta"],
    },
    {
        "catalog_key": "tata-nexon",
        "vehicle_type": "car",
        "make": "Tata",
        "model_name": "Nexon",
        "variant": "",
        "display_name": "Tata Nexon",
        "bike_class": "suv",
        "engine_cc": 1199.0,
        "fuel_tank_capacity_l": 44.0,
        "expected_mileage_kmpl": 17.4,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Tata Motors",
        "official_source_url": "https://cars.tatamotors.com/suv/nexon/ice.html",
        "aliases": ["nexon", "tata nexon"],
    },
    {
        "catalog_key": "hyundai-venue",
        "vehicle_type": "car",
        "make": "Hyundai",
        "model_name": "Venue",
        "variant": "",
        "display_name": "Hyundai Venue",
        "bike_class": "suv",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 45.0,
        "expected_mileage_kmpl": 18.0,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Hyundai Motor India",
        "official_source_url": "https://www.hyundai.com/in/en/find-a-car/venue/highlights",
        "aliases": ["venue", "hyundai venue"],
    },
]


def normalize_bike_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def list_catalog_models() -> list[dict]:
    return [deepcopy(apply_class_defaults(item)) for item in OFFICIAL_BIKE_CATALOG]


def apply_class_defaults(data: dict) -> dict:
    bike_class = data.get("bike_class") or "custom"
    defaults = CLASS_DEFAULTS.get(bike_class, CLASS_DEFAULTS["custom"])
    merged = deepcopy(data)
    for key, value in defaults.items():
        if merged.get(key) in {None, "", 0}:
            merged[key] = value
    return merged


def best_catalog_match(name: str) -> tuple[dict | None, float]:
    normalized = normalize_bike_name(name)
    if not normalized:
        return None, 0

    best_item = None
    best_score = 0.0
    for item in OFFICIAL_BIKE_CATALOG:
        candidates = [item["display_name"], item["model_name"], *item.get("aliases", [])]
        for candidate in candidates:
            score = SequenceMatcher(None, normalized, normalize_bike_name(candidate)).ratio()
            if normalized in normalize_bike_name(candidate) or normalize_bike_name(candidate) in normalized:
                score += 0.08
            if score > best_score:
                best_item = item
                best_score = score
    return (deepcopy(apply_class_defaults(best_item)), min(best_score, 1.0)) if best_item else (None, 0.0)


def build_profile_payload(name: str, vehicle_number: str = "", variant: str = "", make: str = "") -> dict:
    normalized_name = normalize_bike_name(name)
    normalized_make = normalize_bike_name(make)
    search_name = name if not normalized_make or normalized_name.startswith(normalized_make) else f"{make} {name}"
    match, score = best_catalog_match(search_name)
    if match and score >= 0.78:
        match["vehicle_number"] = vehicle_number
        match["usage_pattern"] = match.get("usage_pattern") or ("essential" if match.get("vehicle_type") == "car" else "personal")
        match["estimated_market_value"] = match.get("estimated_market_value") or 0
        match["monthly_income_support"] = match.get("monthly_income_support") or 0
        match["verification_status"] = "official" if score >= 0.92 else "matched"
        match["ai_notes"] = (
            f"Matched against the internal vehicle catalog with confidence {score:.2f}. "
            "Specs are catalog-backed and should still be cross-checked against the owner's manual for exact service intervals."
        )
        return match

    normalized_name = " ".join(part for part in [make.strip(), name.strip()] if part).strip() or "Custom Vehicle"
    inferred_vehicle_type = infer_vehicle_type(normalized_name)
    inferred_class = infer_bike_class(normalized_name)
    defaults = CLASS_DEFAULTS[inferred_class]
    return {
        "vehicle_type": inferred_vehicle_type,
        "catalog_key": "",
        "make": make.strip(),
        "model_name": name.strip() or normalized_name,
        "variant": variant.strip(),
        "display_name": normalized_name,
        "vehicle_number": vehicle_number,
        "bike_class": inferred_class,
        "engine_cc": None,
        "fuel_tank_capacity_l": None,
        "expected_mileage_kmpl": defaults["expected_mileage_kmpl"],
        "service_interval_km": defaults["service_interval_km"],
        "service_interval_days": defaults["service_interval_days"],
        "optimal_cruising_speed_kmph": defaults["optimal_cruising_speed_kmph"],
        "usage_pattern": "essential" if inferred_vehicle_type == "car" else "personal",
        "estimated_market_value": 0,
        "monthly_income_support": 0,
        "official_source_name": "",
        "official_source_url": "",
        "verification_status": "custom",
        "ai_notes": "No confident catalog match yet. Alfred is using class-based heuristics until more documents or usage history are available.",
    }


def infer_bike_class(value: str) -> str:
    normalized = normalize_bike_name(value)
    if any(token in normalized for token in ["creta", "nexon", "suv", "thar", "harrier"]):
        return "suv"
    if any(token in normalized for token in ["dzire", "verna", "city", "sedan"]):
        return "sedan"
    if any(token in normalized for token in ["swift", "i20", "baleno", "altroz", "hatchback"]):
        return "hatchback"
    if any(token in normalized for token in ["ertiga", "carens", "mpv"]):
        return "mpv"
    if any(token in normalized for token in ["adventure", "adv", "strom", "himalayan"]):
        return "adventure"
    if any(token in normalized for token in ["classic", "meteor", "bullet", "hunter", "retro"]):
        return "retro"
    if any(token in normalized for token in ["cruiser", "avenger"]):
        return "cruiser"
    if any(token in normalized for token in ["raider", "sp", "shine", "splendor", "commuter"]):
        return "commuter"
    if any(token in normalized for token in ["rr", "rc", "r15", "ninja", "sport"]):
        return "sport"
    return "roadster"


def infer_vehicle_type(value: str) -> str:
    normalized = normalize_bike_name(value)
    if any(token in normalized for token in ["car", "hatchback", "sedan", "suv", "swift", "dzire", "creta", "nexon", "alto", "baleno"]):
        return "car"
    if any(token in normalized for token in ["scooter", "activa", "jupiter", "ntorq"]):
        return "scooter"
    return "motorcycle"
