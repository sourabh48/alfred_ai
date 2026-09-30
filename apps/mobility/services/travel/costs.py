"""Budget ranges are estimates; provider quotes remain separate dated evidence."""
from math import ceil
from datetime import date

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .money import decimal_amount, quoted_amount, rupees


def calculate_budget(state, destination, *, relaxed_days=0):
    def value(key, default=None):
        return state.get(key, {}).get("value", default)
    days = max(1, min(int(value("trip_duration", 3)), 30))
    people = max(1, min(int(value("number_of_travelers", 1)), 50))
    nights, rooms = max(days-1, 0), ceil(people/2)
    mode = value("transport_mode", "mixed")
    riding = mode in {"ride", "roadtrip"}
    one_way = decimal_amount(destination.get("distance_km") or 250)
    distance = one_way*2+days*25
    nightly = decimal_amount(destination.get("nightly", 1500))
    target = rupees(value("budget", 0) or 0)
    if value("budget_scope") == "per_person":
        target *= people
    if value("budget_type") == "budget" or (target and target < 3000*days*people):
        nightly *= decimal_amount("0.7")
    elif value("budget_type") == "premium":
        nightly *= 2
    mileage = decimal_amount(value("vehicle_mileage") or (30 if mode == "ride" else 14))
    fuel_price = decimal_amount(value("fuel_price_per_litre",110) or 110)
    price_date = value("fuel_price_date")
    fuel_freshness = "USER_PROVIDED" if value("fuel_price_per_litre") else "ESTIMATED"
    if price_date and (timezone.localdate()-date.fromisoformat(price_date)).days > 7:
        fuel_freshness = "CACHED"
    amounts = {"Transport": 0 if riding else rupees(max(1000, one_way*(14 if mode == "flight" else 6))*people),
               "Fuel": rupees(distance/mileage*fuel_price) if riding else 0,
               "Tolls": 400 if mode == "roadtrip" else 0, "Stay": rupees(nightly*nights*rooms),
               "Food": 650*days*people, "Activities": max(0, days-2-relaxed_days)*350*people,
               "Permits": 300*people, "Parking": 100*days if riding else 0,
               "Local Transport": 0 if riding else 350*days*people}
    formulas = {"Fuel": f"({one_way} km × 2 + {days} × 25 local km) ÷ {mileage} km/l × INR {fuel_price}/l" if riding else "No fuel allowance for this mode",
                "Transport": f"max(1000, {one_way} km × {14 if mode == 'flight' else 6}) × {people} travellers; allowance only" if not riding else "Own vehicle",
                "Stay": f"INR {nightly:g} × {nights} nights × {rooms} rooms",
                "Food": f"INR 650 × {days} days × {people} travellers",
                "Activities": f"max(0, {days} − 2 − {relaxed_days}) × INR 350 × {people}",
                "Permits": f"INR 300 × {people}; contingency, not a permit fee",
                "Tolls": "INR 400 car allowance; other modes 0 allowance, actual toll liability unknown",
                "Parking": f"INR 100 × {days} days" if riding else "No parking allowance",
                "Local Transport": f"INR 350 × {days} days × {people}" if not riding else "Included in local fuel distance"}
    quotes = []
    for quote in destination.get("selected_price_snapshots", []) or []:
        if not isinstance(quote, dict):
            continue
        try:
            expires = parse_datetime(quote.get("expires_at") or "")
            total = decimal_amount(quote.get("total"))
            total_text = quoted_amount(total)
        except (TypeError, ValueError):
            # Malformed evidence cannot qualify as a verified price.
            continue
        # A quote cannot cover a budget category unless its scope and currency match.
        if (isinstance(quote.get("category"), str) and quote["category"] in amounts and quote.get("currency") == "INR"
                and quote.get("scope") == "whole_trip" and quote.get("availability") == "available"
                and isinstance(quote.get("source_url"), str) and quote["source_url"]
                and expires and timezone.is_aware(expires) and expires > timezone.now()
                and total < 100_000_000):
            quotes.append({**quote, "total": total_text})
    # Quotes are displayed separately; budget assumptions never silently become bookings.
    amounts["Emergency Buffer"] = rupees(sum(amounts.values())*decimal_amount("0.15"))
    formulas["Emergency Buffer"] = "15% × sum of other budget allowances"
    expected = sum(amounts.values())
    line_items = [{"category": k, "low": rupees(v*decimal_amount("0.8")), "expected": v, "high": rupees(v*decimal_amount("1.2")),
                   "freshness": "ESTIMATED", "formula": formulas[k],
                   "input_freshness": fuel_freshness if k == "Fuel" else "ESTIMATED"} for k, v in amounts.items()]
    low, high = sum(i["low"] for i in line_items), sum(i["high"] for i in line_items)
    assumptions = [f"{people} traveller(s), {days} days, {nights} nights; {rooms} shared room(s).",
        "INR estimates, not quotes or confirmed availability. Meals estimated at INR 650 per person/day.",
        f"Fuel: INR {fuel_price}/litre ({fuel_freshness}); mileage {mileage} km/l. Pillion, terrain, load and weather can change consumption.",
        "Round-trip route plus 25 local km/day; return routing may differ. Low/high ranges are planning allowances, not statistical confidence intervals."]
    if not destination.get("distance_km"):
        assumptions.append("Distance unavailable: 250 km each way used solely for a provisional budget.")
    if not riding:
        assumptions.append("Transport allowance only; no train/flight fare or seat availability verified.")
    return {"categories": amounts, "line_items": line_items, "minimum": low, "low": low,
            "expected": expected, "comfortable": high, "high": high, "target": target,
            "currency": "INR", "scope": "whole_trip", "freshness": "ESTIMATED", "verified_prices": quotes,
            "transport_mode": mode, "over_budget": max(0, expected-target) if target else 0,
            "assumptions": assumptions,
            "adaptations": ["Choose a budget homestay", "Remove paid activities", "Try a nearer destination or shorten the trip"] if target and expected > target else []}
