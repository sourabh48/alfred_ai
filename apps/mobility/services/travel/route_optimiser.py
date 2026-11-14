"""Exact multi-stop route optimiser: ALFRED computes the visiting order in code; a model may only explain it.

Times are hours from Day 1 00:00 (Day 2 08:00 is 32). Every subset of stops is tried in every order
(depth-first, so an infeasible prefix prunes its extensions) and each order is scheduled greedily at
the earliest feasible time, which is exact for these rules.
"""
from math import floor

MAX_STOPS = 8  # 8 stops is ~110k orders; beyond that exhaustive search stops being fast.
EPS = 1e-9


def optimise_route(start, end, stops, ride_hours, rules=None, start_at=0):
    """Best order by total score, ties to the fewest riding hours; None if not even start→end fits.

    stops: [{"name", "visit_hours", "score"}]. ride_hours: {(a, b): hours}, either direction is enough.
    rules (each optional, omitted = no limit): day_start/day_end (hour of day riding and visits are
    allowed), max_ride_hours_per_day, deadline. Rides and visits are never split across days.
    """
    rules = rules or {}
    if len(stops) > MAX_STOPS:
        raise ValueError(f"Route optimisation is limited to {MAX_STOPS} stops.")
    names = [s["name"] for s in stops]
    if len(set(names)) != len(names) or start in names or end in names:
        raise ValueError("Stop names must be distinct and differ from the start and end.")
    if any(s["visit_hours"] < 0 or s["score"] < 0 for s in stops):
        raise ValueError("Visit hours and scores cannot be negative.")
    day_start, day_end = rules.get("day_start"), rules.get("day_end")
    window = day_start is not None and day_end is not None
    cap, deadline = rules.get("max_ride_hours_per_day"), rules.get("deadline")

    def ride(a, b):
        if a == b:
            return 0
        hours = ride_hours.get((a, b), ride_hours.get((b, a)))
        if hours is None or hours < 0:
            raise ValueError(f"No valid ride time between {a} and {b}.")
        return hours

    def place(t, day, rode, hours, riding):
        """Earliest start for an unsplittable activity: (start, day, ridden that day) or None."""
        for _ in range(2):  # today, else a fresh next day; failing both means it never fits
            if floor(t / 24) != day:
                day, rode = floor(t / 24), 0
            if window:
                t = max(t, day * 24 + day_start)
            if ((not window or t + hours <= day * 24 + day_end + EPS)
                    and (not riding or cap is None or rode + hours <= cap + EPS)):
                return t, day, rode + hours * riding
            if not window and cap is None:
                return None
            t = (day + 1) * 24
        return None

    best, equal = None, []

    def visit(here, t, day, rode, score, total, order, steps, left):
        nonlocal best, equal
        hours = ride(here, end)
        placed = place(t, day, rode, hours, True)
        if placed and (deadline is None or placed[0] + hours <= deadline + EPS):
            key = (round(score, 6), -round(total + hours, 6))
            if best is None or key > best["key"]:
                best = {"key": key, "stops": order, "steps": steps + [("ride", here, end, placed[0], hours)]}
                equal = [order]
            elif key == best["key"]:
                equal.append(order)
        for stop in left:
            hours = ride(here, stop["name"])
            placed = place(t, day, rode, hours, True)
            if not placed:
                continue
            arrive = placed[0] + hours
            stay = place(arrive, placed[1], placed[2], stop["visit_hours"], False)
            if not stay or (deadline is not None and stay[0] + stop["visit_hours"] > deadline + EPS):
                continue  # later stops only finish later, so this prefix and its extensions are out
            visit(stop["name"], stay[0] + stop["visit_hours"], stay[1], stay[2], score + stop["score"],
                  total + hours, order + [stop["name"]],
                  steps + [("ride", here, stop["name"], placed[0], hours), ("visit", stop["name"], None, stay[0], stop["visit_hours"])],
                  [s for s in left if s is not stop])

    visit(start, start_at, floor(start_at / 24), 0, 0, 0, [], [], list(stops))
    if best is None:
        return None
    clock = lambda h: f"{int(round(h * 60)) // 60:02d}:{int(round(h * 60)) % 60:02d}"
    schedule = []
    for kind, a, b, begin, hours in best["steps"]:
        day = floor(begin / 24)
        if not schedule or schedule[-1]["day"] != day + 1:
            schedule.append({"day": day + 1, "items": []})
        item = {"type": kind, "start": clock(begin - day * 24), "end": clock(begin + hours - day * 24), "hours": hours}
        item.update({"from": a, "to": b} if kind == "ride" else {"place": a})
        schedule[-1]["items"].append(item)
    return {"score": best["key"][0], "ride_hours": -best["key"][1], "stops": best["stops"],
            "schedule": schedule, "equal_orders": equal}
