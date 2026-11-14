"""The multi-stop order is computed exactly in code, never searched by a model."""
from itertools import permutations
from time import perf_counter

from django.test import SimpleTestCase

from apps.mobility.services.travel.route_optimiser import MAX_STOPS, optimise_route

RULES = {"day_start": 7, "day_end": 18, "max_ride_hours_per_day": 7, "deadline": 2*24 + 18}  # back by Day 3 18:00
STOPS = [{"name": n, "visit_hours": h, "score": s} for n, h, s in
         (("Mysuru", 4, 6), ("Coorg", 5, 8), ("Chikmagalur", 4, 7), ("Ooty", 5, 8), ("Hampi", 6, 9))]
RIDE = {("Bengaluru", "Mysuru"): 3, ("Bengaluru", "Coorg"): 5.5, ("Bengaluru", "Chikmagalur"): 5,
        ("Bengaluru", "Ooty"): 6.5, ("Bengaluru", "Hampi"): 6.5, ("Mysuru", "Coorg"): 3,
        ("Mysuru", "Chikmagalur"): 4, ("Mysuru", "Ooty"): 3.5, ("Mysuru", "Hampi"): 7.5,
        ("Coorg", "Chikmagalur"): 4, ("Coorg", "Ooty"): 5.5, ("Coorg", "Hampi"): 8,
        ("Chikmagalur", "Ooty"): 7, ("Chikmagalur", "Hampi"): 5.5, ("Ooty", "Hampi"): 10}


class RouteOptimiserTests(SimpleTestCase):
    def test_karnataka_reference_trip(self):
        best = optimise_route("Bengaluru", "Bengaluru", STOPS, RIDE, RULES, start_at=8)
        self.assertEqual((best["score"], best["ride_hours"]), (21, 15))
        self.assertEqual(best["stops"], ["Mysuru", "Coorg", "Chikmagalur"])
        self.assertEqual(best["equal_orders"], [["Mysuru", "Coorg", "Chikmagalur"], ["Chikmagalur", "Coorg", "Mysuru"]])
        self.assertEqual([[(i["type"], i["start"], i["end"]) for i in d["items"]] for d in best["schedule"]], [
            [("ride", "08:00", "11:00"), ("visit", "11:00", "15:00"), ("ride", "15:00", "18:00")],
            [("visit", "07:00", "12:00"), ("ride", "12:00", "16:00")],
            [("visit", "07:00", "11:00"), ("ride", "11:00", "16:00")]])
        self.assertEqual([d["day"] for d in best["schedule"]], [1, 2, 3])
        self.assertEqual(best["schedule"][2]["items"][1], {"type": "ride", "from": "Chikmagalur", "to": "Bengaluru",
                                                           "start": "11:00", "end": "16:00", "hours": 5})

    def test_infeasible_trip_returns_none(self):
        # The only ride home is longer than a day's riding limit.
        self.assertIsNone(optimise_route("A", "B", STOPS[:1], {("A", "B"): 8, ("A", "Mysuru"): 1, ("Mysuru", "B"): 8},
                                         RULES, start_at=8))
        # A deadline before the direct ride can finish.
        self.assertIsNone(optimise_route("A", "B", [], {("A", "B"): 3}, {"deadline": 10}, start_at=8))

    def test_stop_that_cannot_fit_is_left_out(self):
        best = optimise_route("Bengaluru", "Bengaluru", [{"name": "Far", "visit_hours": 1, "score": 50}, STOPS[0]],
                              {**RIDE, ("Bengaluru", "Far"): 7.5, ("Far", "Mysuru"): 1}, RULES, start_at=8)
        self.assertEqual((best["stops"], best["score"], best["ride_hours"]), (["Mysuru"], 6, 6))

    def test_score_first_then_fewest_riding_hours(self):
        stops = [{"name": n, "visit_hours": 1, "score": s} for n, s in (("Near", 5), ("Far", 5), ("Best", 6))]
        ride = {("H", "Near"): 1, ("H", "Far"): 3, ("H", "Best"): 4, ("Near", "Far"): 20, ("Near", "Best"): 9, ("Far", "Best"): 9}
        # One stop only: the higher score wins although it rides longest.
        best = optimise_route("H", "H", stops, ride, {"max_ride_hours_per_day": 8}, start_at=8)
        self.assertEqual((best["stops"], best["ride_hours"]), (["Best"], 8))
        # Equal scores (either stop alone fits by 15:00, both never do): fewer riding hours wins.
        best = optimise_route("H", "H", stops[:2], ride, {"deadline": 15}, start_at=8)
        self.assertEqual((best["stops"], best["score"], best["ride_hours"], best["equal_orders"]), (["Near"], 5, 2, [["Near"]]))

    def test_every_equal_order_is_returned_and_matches_brute_force(self):
        stops = [{"name": n, "visit_hours": 0, "score": 1} for n in "abc"]
        ride = {(x, y): 1 for x in "Habc" for y in "Habc" if x < y}
        best = optimise_route("H", "H", stops, ride)
        self.assertEqual(sorted(best["equal_orders"]), sorted(map(list, permutations("abc"))))
        self.assertEqual(best["stops"], ["a", "b", "c"])

    def test_stop_cap(self):
        stops = [{"name": f"S{i}", "visit_hours": 1, "score": 1} for i in range(MAX_STOPS + 1)]
        ride = {(a, b): 1 for a in ["H", *(s["name"] for s in stops)] for b in (s["name"] for s in stops) if a != b}
        with self.assertRaises(ValueError):
            optimise_route("H", "H", stops, ride)
        began = perf_counter()
        best = optimise_route("H", "H", stops[:MAX_STOPS], ride)  # no rules: nothing prunes, all ~110k orders
        self.assertLess(perf_counter() - began, 10)
        self.assertEqual((best["score"], best["ride_hours"], len(best["equal_orders"])), (MAX_STOPS, MAX_STOPS + 1, 40320))

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            optimise_route("H", "H", [STOPS[0], STOPS[0]], RIDE)
        with self.assertRaises(ValueError):
            optimise_route("H", "H", [STOPS[0]], {})
