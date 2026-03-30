from __future__ import annotations

from datetime import date

from apps.mobility.models import BikeProfile
from apps.mobility.services.bike_service_intelligence import bike_service_intelligence
from apps.integrations.services import verified_intelligence


class TravelAdvisorService:
    def build_advice(
        self,
        user,
        destination: str,
        start_date: date,
        end_date: date,
        budget: float,
        transport_mode: str,
        vehicle_profile: BikeProfile | None = None,
    ) -> dict:
        duration_days = max((end_date - start_date).days + 1, 1)
        per_day_budget = round((budget or 0) / duration_days, 2) if duration_days else 0
        evidence = []
        geocode = verified_intelligence.geocode_destination(destination) if destination else None
        destination_match = geocode.payload if geocode else None
        if geocode:
            evidence.append(geocode.evidence)
        weather = self._weather(destination_match, start_date, end_date, evidence) if destination_match else self._empty_weather()
        nearby = self._nearby_offbeat(destination, evidence) if destination else []
        stay_advice = self._stay_advice(user, per_day_budget, duration_days)
        bike_summary = bike_service_intelligence.build_dashboard(user)
        primary_bike = vehicle_profile or BikeProfile.objects.filter(user=user).order_by("-is_primary", "-updated_at").first()

        feasibility = self._feasibility_message(per_day_budget, weather, transport_mode, duration_days)
        bike_readiness = self._bike_readiness(primary_bike, bike_summary)

        return {
            "destination_match": destination_match or {"display_name": destination, "latitude": None, "longitude": None},
            "weather": weather,
            "offbeat_suggestions": nearby,
            "stay_advice": stay_advice,
            "feasibility": feasibility,
            "bike_readiness": bike_readiness,
            "itinerary_outline": self._itinerary_outline(destination, duration_days, weather),
            "cost_lens": {
                "trip_budget": round(budget or 0, 2),
                "per_day_budget": per_day_budget,
                "recommended_stay_cap_per_night": stay_advice["recommended_room_cap"],
                "service_buffer": bike_readiness["suggested_service_buffer"],
            },
            "evidence": evidence,
        }

    def _weather(self, location: dict, start_date: date, end_date: date, evidence: list[dict]) -> dict:
        today = date.today()
        if (start_date - today).days > 15:
            return {
                "status": "seasonal_only",
                "summary": "Live forecast is not yet available for these dates. Recheck within 15 days of travel.",
                "average_max_temp": None,
                "average_min_temp": None,
                "precipitation_total": None,
                "wind_max": None,
            }

        try:
            weather = verified_intelligence.weather_snapshot(location["latitude"], location["longitude"], start_date, end_date)
            evidence.append(weather.evidence)
            average_max = weather.payload.get("average_max_temp")
            average_min = weather.payload.get("average_min_temp")
            precipitation_total = weather.payload.get("precipitation_total")
            wind_max = weather.payload.get("wind_max")
            if precipitation_total and precipitation_total >= 20:
                summary = "Wet-weather gear is strongly advised. Rain impact on roads and visibility is likely."
            elif average_max and average_max >= 33:
                summary = "Expect hot riding conditions. Plan earlier starts, hydration stops, and lighter afternoon mileage."
            else:
                summary = "Weather looks broadly manageable for a bike-led itinerary."
            return {
                "status": "live",
                "summary": summary,
                "average_max_temp": average_max,
                "average_min_temp": average_min,
                "precipitation_total": precipitation_total,
                "wind_max": wind_max,
            }
        except Exception:
            return self._empty_weather()

    def _empty_weather(self) -> dict:
        return {
            "status": "unavailable",
            "summary": "Weather data could not be fetched right now.",
            "average_max_temp": None,
            "average_min_temp": None,
            "precipitation_total": None,
            "wind_max": None,
        }

    def _nearby_offbeat(self, destination: str, evidence: list[dict]) -> list[dict]:
        try:
            result = verified_intelligence.offbeat_suggestions(destination)
            evidence.append(result.evidence)
            return result.payload.get("results", [])[:6]
        except Exception:
            return []

    def _stay_advice(self, user, per_day_budget: float, duration_days: int) -> dict:
        income = getattr(user, "monthly_income", 0) or 0
        room_cap = round(min(max(per_day_budget * 0.42, 900), 4500), 2) if per_day_budget else 1500
        if income >= 100000 and room_cap >= 2500:
            tier = "semi-budget to comfortable"
        elif income >= 50000:
            tier = "budget to semi-budget"
        else:
            tier = "budget"
        return {
            "tier": tier,
            "recommended_room_cap": room_cap,
            "notes": (
                f"For a {duration_days}-day trip, keep nightly stays near INR {room_cap:,.0f} "
                "so food, fuel, and repair buffer remain inside the trip budget."
            ),
        }

    def _feasibility_message(self, per_day_budget: float, weather: dict, transport_mode: str, duration_days: int) -> dict:
        rating = "good"
        reasons = []
        if per_day_budget and per_day_budget < 1800:
            rating = "tight"
            reasons.append("Budget per day is tight for fuel, stay, and contingencies.")
        if weather.get("precipitation_total") and weather["precipitation_total"] >= 20:
            rating = "guarded"
            reasons.append("Rainfall could materially slow the route.")
        if transport_mode == "ride" and duration_days <= 2:
            reasons.append("Keep the day-one route short and avoid aggressive mileage targets.")
        if not reasons:
            reasons.append("Budget, duration, and current forecast look workable.")
        return {"rating": rating, "reasons": reasons}

    def _bike_readiness(self, bike: BikeProfile | None, bike_summary: dict) -> dict:
        summary = bike_summary.get("summary", {})
        due_date = summary.get("next_service_date")
        due_km = summary.get("next_service_km")
        expected_mileage = bike.expected_mileage_kmpl if bike and bike.expected_mileage_kmpl else 0
        tank = bike.fuel_tank_capacity_l if bike and bike.fuel_tank_capacity_l else 0
        estimated_range = round(expected_mileage * tank, 1) if expected_mileage and tank else 0
        recommendation = "Bike looks broadly ready from the current data."
        if summary.get("critical_faults"):
            recommendation = "Resolve critical faults before a long ride."
        elif summary.get("expiring_documents") or summary.get("expired_documents"):
            recommendation = "Renew or verify bike documents before departure."
        elif due_date or due_km:
            recommendation = "Cross-check the next service window before committing to a long route."
        return {
            "bike_name": bike.display_name if bike else "",
            "vehicle_type": bike.get_vehicle_type_display() if bike else "",
            "estimated_mileage_kmpl": expected_mileage,
            "estimated_range_km": estimated_range,
            "next_service_date": due_date,
            "next_service_km": due_km,
            "suggested_service_buffer": round(max((summary.get("projected_next_service_cost") or 0) * 0.35, 800), 2),
            "recommendation": recommendation,
        }

    def _itinerary_outline(self, destination: str, duration_days: int, weather: dict) -> list[str]:
        plan = []
        if duration_days <= 1:
            plan.append(f"Leave early, keep {destination} as the anchor stop, and return before late-night fatigue sets in.")
        else:
            plan.append(f"Day 1: ride to {destination}, settle in, and keep the first evening easy.")
            plan.append("Mid-trip day: cover one main attraction plus one quieter side route or viewpoint.")
            plan.append("Final day: keep a repair/fuel buffer and start the return leg early.")
        if weather.get("precipitation_total") and weather["precipitation_total"] >= 20:
            plan.append("Build rain delay margin into the itinerary and keep luggage waterproofed.")
        elif weather.get("average_max_temp") and weather["average_max_temp"] >= 33:
            plan.append("Use early morning riding blocks and longer midday hydration breaks.")
        return plan[:4]


travel_advisor = TravelAdvisorService()
