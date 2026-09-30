from copy import deepcopy
from datetime import date, timedelta
import re
from rest_framework.exceptions import ValidationError

from .travel_discovery import budget_for, value
from .travel_catalog import ACTIVITY_TAGS
from .travel.money import decimal_amount, rupees


def build_itinerary(state, destination):
    days = int(value(state, "trip_duration", 3))
    if not 1 <= days <= 30:
        raise ValidationError("Choose a 1–30 day window for this itinerary. Your existing saved trip is retained.")
    budget = budget_for(state, destination)
    start = value(state, "available_start_date")
    origin = value(state, "origin", "your starting city")
    mode = value(state, "transport_mode", "mixed")
    earliest = int(value(state, "earliest_departure_hour", 8))
    activities = destination.get("activities", [])
    itinerary_days = []
    avoid = value(state, "must_avoid", [])
    for n in range(1, days+1):
        first, last = n == 1, n == days
        items = []
        if first or last:
            leg = f"{origin} → {destination['name']}" if first else f"{destination['name']} → {origin}"
            if days == 1:
                leg += f" → {origin}"
            items.append({"title": leg, "priority": "Must Do", "period": f"After {earliest:02d}:00; plan to arrive in daylight",
                          "duration": f"~{destination.get('travel_hours') or 'unknown'} hours per leg, plus breaks; estimate only",
                          "type": "travel", "cost": 0})
            items.append({"title": "Meal, hydration and rest stops", "priority": "Must Do", "period": "At comfortable intervals",
                          "duration": "20–30 minutes per break; stop sooner if tired", "type": "break", "cost": 0})
        if not last or days == 1:
            chosen = activities[:1] if first else activities[(n-2) % max(1, len(activities)):] or activities[:1]
            for title in chosen[:1 if first else 2]:
                tags = ACTIVITY_TAGS.get(title, [])
                if any(word in title.lower() or word in tags for word in avoid):
                    continue
                items.append({"title": title, "priority": "Recommended", "period": "Afternoon, if travel allows" if first else "Late morning / afternoon",
                              "duration": "Allow 1–2 hours; confirm hours and access" + ("; includes walking/climbing" if tags else ""), "type": "trekking" if "trekking" in tags else "activity", "cost": 0 if first else 350})
            items.append({"title": "Local meal and easy photography walk", "priority": "Optional", "period": "Before dark",
                          "duration": "45–60 minutes; choose a public, accessible area", "type": "photography", "cost": 0})
        items.append({"title": "Café, local food or indoor rest if rain / closures disrupt plans", "priority": "Backup",
                      "period": "Flexible", "duration": "Replace an outdoor activity", "type": "backup", "cost": 0})
        itinerary_days.append({"day": n, "date": (date.fromisoformat(start)+timedelta(days=n-1)).isoformat() if start else None,
            "title": "Travel and settle in" if first else "Return home" if last else "Explore at your pace",
            "pace": "balanced", "items": items, "stay": destination["stay"] if not last else "Home",
            "meals": "Local breakfast and simple meals; ask about dietary needs and check hygiene.",
            "estimated_cost": budget["expected"]//days + (budget["expected"] % days if last else 0)})
    paid_items = [item for day in itinerary_days for item in day["items"] if item["cost"]]
    for index, item in enumerate(paid_items):
        item["cost"] = budget["categories"]["Activities"]//len(paid_items) + (budget["categories"]["Activities"] % len(paid_items) if index == len(paid_items)-1 else 0)
        item["cost_note"] = "Share of the activity allowance; not a verified entry fee."
    if value(state, "food_preferences"):
        for day in itinerary_days:
            day["meals"] += " Your preference: " + value(state, "food_preferences") + "."
    packing = ["Weather-appropriate clothing", "Water and personal medicines", "ID and booking confirmations", "Power bank and offline maps"]
    bike = None
    if mode == "ride":
        packing += ["Helmet and riding protection", "Rain gear and waterproof luggage", "Puncture kit", "Vehicle documents", "Check tyres, brakes and chain/lube before departure"]
        mileage, tank = value(state, "vehicle_mileage"), value(state, "vehicle_tank_litres")
        bike = {"profile": value(state, "vehicle_name", "No vehicle profile selected"),
                "condition": value(state, "vehicle_condition", {}),
                "nominal_range_km": round(mileage*tank) if mileage and tank and mileage > 0 and tank > 0 else None,
                "range_note": "Mileage × tank capacity from your profile; practical range varies. Identify open fuel stations before riding and refuel with a reserve.",
                "pillion": value(state, "pillion", False),
                "notes": "Allow more breaks with pillion/luggage. Avoid unverified shortcuts and unpaved routes; do not ride through flooded roads."}
    return {"destination": destination["name"], "origin": origin, "summary": f"{days} days in {destination['name']} with flexible activity blocks.",
        **{key:deepcopy(destination.get(key, [] if key in {"weather_proposals","mode_comparison","web_research","external_links"} else {})) for key in
           ("route_result","weather_result","places_result","permit_result","hotels_result","flights_result","trains_result","buses_result","discovery_result","weather_proposals","map","quality","mode_comparison","web_research","external_links")},
        "status": "preliminary", "days": itinerary_days, "budget": budget, "weather": destination["weather"],
        "route": {"summary": f"{origin} → {destination['name']} → {origin}", "distance_km_one_way": destination.get("distance_km"),
                  "hours_one_way": destination.get("travel_hours"), "confidence": destination.get("route_result",{}).get("confidence","ESTIMATED"),
                  "note": destination.get("distance_basis","Town-centre estimate only.") + " Confirm a legal route, closures and fuel stops before departure.",
                  "options": [{"name": "Fastest", "status": "Needs current routing verification"},
                              {"name": "Scenic", "status": "Use verified public roads only; no shortcut suggested"},
                              {"name": "Easier", "status": "Prefer main roads; add an overnight stop if travel exceeds your comfort limit"}]},
        "bike": bike, "packing": packing, "sources": destination.get("sources", []),
        "checks": (["The estimated travel leg exceeds your daily distance preference. Choose a nearer destination or add an overnight stop before confirming the route."] if destination.get("distance_km",0) and destination["distance_km"]*(2 if days == 1 else 1)>value(state,"maximum_daily_driving",300) else []) + ["Verify permits, entry fees, parking and opening hours before committing.",
                   "Sunrise/sunset times and safe viewpoints are unverified; daylight is a planning constraint, not a promised photography slot.",
                   "Accommodation is an area and allowance, not a booking."] + destination.get("issues", []),
        "edits": []}


def edit_itinerary(itinerary, text, state):
    result = deepcopy(itinerary)
    lower = text.lower()
    match = re.search(r"day\s*(\d+)", lower)
    day_number = int(match[1]) if match else None
    if day_number and not 1 <= day_number <= len(result["days"]):
        return None, "That day is outside this itinerary. Which day should I change?"
    changed = False
    activity_discount = 0
    stay_discount = 0
    target_days = [d for d in result["days"] if not day_number or d["day"] == day_number]
    if any(w in lower for w in ("relax", "too busy", "slow")):
        for day in target_days:
            day["pace"] = "relaxed"
            kept = []
            activity_count = 0
            for item in day["items"]:
                if item["type"] in {"activity", "photography", "trekking"}:
                    activity_count += 1
                    if activity_count > 1:
                        activity_discount += item.get("cost", 0)
                        day["estimated_cost"] = max(0, day["estimated_cost"]-item.get("cost", 0))
                        continue
                kept.append(item)
            day["items"] = kept
            day["title"] = "A relaxed day with one main activity"
        changed = True
    if "remove" in lower or "no trek" in lower:
        term = "trek" if "trek" in lower else "photography" if "photo" in lower else None
        if term:
            for day in target_days:
                removed = [i for i in day["items"] if term in i["title"].lower() or term in i["type"]]
                reduction = sum(i.get("cost",0) for i in removed)
                activity_discount += reduction
                day["estimated_cost"] = max(0,day["estimated_cost"]-reduction)
                day["items"] = [i for i in day["items"] if i not in removed]
            changed = True
    if "waterfall" in lower or "camping" in lower:
        chosen = next((d for d in target_days if 1 < d["day"] < len(result["days"])), target_days[0])
        activity = "Waterfall visit, subject to access and weather checks" if "waterfall" in lower else "Licensed campsite enquiry; replace stay only after confirmation"
        chosen["items"].append({"title": activity, "priority": "Optional", "period": "Flexible", "duration": "1–2 hours; verify location and permission first",
                                "type": "activity", "cost": 0, "cost_note": "Not quoted; included in activity allowance only if affordable"})
        changed = True
    if "wake" in lower or "start" in lower and "8" in lower:
        for day in result["days"]:
            for item in day["items"]:
                if item["type"] == "travel":
                    item["period"] = "After 08:00; shorten the leg or stay overnight if daylight is insufficient"
        changed = True
    if "return" in lower and "short" in lower:
        result["route"]["note"] += " Split the return across the last two days; choose a verified overnight town before finalising the route and recosting the stay."
        result["days"][-1]["title"] = "Shorter return leg (overnight stop still to choose)"
        changed = True
    if "budget" in lower or "cheaper" in lower:
        old = result["budget"]["categories"]["Stay"]
        floor = 600 * max(0,len(result["days"])-1) * max(1,(value(state,"number_of_travelers",1)+1)//2)
        new = max(min(old,floor),rupees(decimal_amount(old) * decimal_amount("0.75")))
        stay_discount += old-new
        result["budget"]["categories"]["Stay"] = new
        nights = max(1, len(result["days"])-1)
        for day in result["days"][:-1]:
            reduction = (old-new)//nights + ((old-new) % nights if day["day"] == nights else 0)
            day["estimated_cost"] = max(0, day["estimated_cost"]-reduction)
        result["budget"]["assumptions"].append("Budget edit: lower stay allowance by up to 25%, keeping a ₹600/room/night planning floor; verify a suitable stay before booking.")
        changed = True
    if not changed:
        return None, "I haven't changed your itinerary. Try ‘Make day 2 relaxed’, ‘Remove trekking’, ‘Add one waterfall’, or ‘Reduce the budget’."
    discount = activity_discount + stay_discount
    if discount:
        result["budget"]["categories"]["Activities"] = max(0, result["budget"]["categories"]["Activities"]-activity_discount)
        result["budget"]["expected"] = max(0, result["budget"]["expected"]-discount)
        result["budget"]["low"] = result["budget"]["minimum"] = rupees(decimal_amount(result["budget"]["expected"]) * decimal_amount("0.8"))
        result["budget"]["high"] = result["budget"]["comfortable"] = rupees(decimal_amount(result["budget"]["expected"]) * decimal_amount("1.2"))
        result["budget"]["over_budget"] = max(0, result["budget"]["expected"]-result["budget"]["target"]) if result["budget"]["target"] else 0
    if value(state, "budget"):
        result["budget"]["target"] = rupees(value(state, "budget")) * (value(state, "number_of_travelers", 1) if value(state, "budget_scope") == "per_person" else 1)
        result["budget"]["over_budget"] = max(0, result["budget"]["expected"]-result["budget"]["target"])
    if discount and result["budget"].get("line_items"):
        for item in result["budget"]["line_items"]:
            amount = result["budget"]["categories"][item["category"]]
            if amount != item["expected"]:
                item["formula"] = f"Revised {item['category'].lower()} allowance after your itinerary edit: INR {amount}"
            if item["category"] == "Emergency Buffer":
                item["formula"] = "Original emergency buffer retained after reducing other allowances"
            item.update(low=rupees(decimal_amount(amount) * decimal_amount("0.8")), expected=amount,
                        high=rupees(decimal_amount(amount) * decimal_amount("1.2")))
        result["budget"]["low"] = result["budget"]["minimum"] = sum(i["low"] for i in result["budget"]["line_items"])
        result["budget"]["high"] = result["budget"]["comfortable"] = sum(i["high"] for i in result["budget"]["line_items"])
    result["edits"].append({"request": text, "day": day_number})
    return result, f"Updated {f'day {day_number}' if day_number else 'your plan'}. " + ("The other days are unchanged." if day_number else "Review the revised allowances before booking.")
