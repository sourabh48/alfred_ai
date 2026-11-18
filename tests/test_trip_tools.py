"""Trip tools: bookings, confirmation reading, a recorded GPX ride and imported places. Synthetic data, no network."""
import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.mobility.models import TravelPlan, TravelProviderState
from apps.mobility.services.travel import trip_tools

CONFIRMATION = """Your booking is confirmed.
Booking reference: QX7P2L
Flight AI 864 from Pune to Delhi
Departure: 12 Dec 2026, 07:45
Total paid: INR 6,420.00
"""


class Reasoner:
    def __init__(self, reply):
        self.reply = reply

    def reason(self, payload, *, max_output_tokens, deadline):
        return self.reply


def gpx(points):
    rows = "".join(f'<trkpt lat="{lat}" lon="{lon}"><ele>{ele}</ele><time>2026-12-12T07:{minute:02d}:00Z</time></trkpt>'
                   for minute, (lat, lon, ele) in enumerate(points))
    return f'<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1"><trk><trkseg>{rows}</trkseg></trk></gpx>'.encode()


class TripToolsTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner, self.other = users.create_user("trip-owner", password="pw-12345678"), users.create_user("trip-other", password="pw-12345678")
        self.plan = TravelPlan.objects.create(user=self.owner, title="Delhi", destination="Delhi", start_date=date(2026, 12, 12),
                                              end_date=date(2026, 12, 15), itinerary={"route": {"distance_km_total": 2.0}})
        self.url = f"/api/mobility/travel-plans/{self.plan.pk}/tools/"
        self.client.force_login(self.owner)

    def post(self, **body):
        return self.client.post(self.url, body, content_type="application/json")

    def test_bookings_are_recorded_validated_and_private(self):
        booking = {"kind": "flight", "title": "AI 864 Pune to Delhi", "confirmation": "QX7P2L", "start": "2026-12-12T07:45",
                   "amount": "6,420", "currency": "inr"}
        saved = self.post(operation="booking_add", booking=booking).json()["bookings"]
        self.assertEqual((saved[0]["amount"], saved[0]["currency"], saved[0]["start"]), ("6420.00", "INR", "2026-12-12T07:45"))
        self.assertEqual(len(self.post(operation="booking_add", booking=booking).json()["bookings"]), 1)  # same booking twice
        self.assertEqual(self.post(operation="booking_add", booking={**booking, "amount": "5", "currency": ""}).status_code, 400)
        self.assertEqual(self.post(operation="booking_add", booking={**booking, "end": "2026-12-01"}).status_code, 400)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.post(operation="booking_remove", id=saved[0]["id"]).json()["bookings"], [])

    def test_confirmation_reader_keeps_only_fields_written_in_the_confirmation(self):
        reply = json.dumps({"kind": "flight", "title": "Flight AI 864 from Pune to Delhi", "confirmation": "QX7P2L",
                            "start_as_written": "12 Dec 2026, 07:45", "start": "2026-12-12T07:45", "end_as_written": "15 Dec 2026",
                            "end": "2026-12-15", "provider": "SkyCheap Travel", "amount_as_written": "INR 6,420.00", "currency": "INR"})
        draft = trip_tools.read_confirmation(CONFIRMATION, reasoner=Reasoner(reply))["draft"]
        self.assertEqual(draft["title"], "Flight AI 864 from Pune to Delhi")
        self.assertEqual((draft["start"], draft["amount"], draft["currency"]), ("2026-12-12T07:45", "6420.00", "INR"))
        self.assertNotIn("provider", draft)  # not in the confirmation, so invented
        self.assertNotIn("end", draft)
        broken = trip_tools.read_confirmation(CONFIRMATION, reasoner=Reasoner("no json here"))
        self.assertEqual(broken["draft"]["confirmation"], "QX7P2L")  # the plain rule still finds the code

    def test_recorded_ride_gives_climb_time_profile_and_plan_difference(self):
        points = [(18.5, 73.8 + i * 0.001, 500 + (i * 2 if i <= 20 else 40 - (i - 20))) for i in range(41)]
        response = self.client.post(self.url, {"operation": "ride", "file": SimpleUploadedFile("ride.gpx", gpx(points))})
        ride = response.json()["ride"]
        self.assertAlmostEqual(ride["distance_km"], 4.22, delta=0.05)
        self.assertEqual((ride["ascent_m"], ride["highest_m"], ride["lowest_m"]), (40, 540, 500))
        self.assertEqual(ride["total_hours"], 0.67)
        self.assertEqual(ride["compare"]["planned_km"], 2.0)
        self.assertGreater(ride["steepest_climb_pct"], 0)
        self.assertTrue(ride["profile"])
        bad = self.client.post(self.url, {"operation": "ride", "file": SimpleUploadedFile("ride.gpx", b'<!DOCTYPE x [<!ENTITY a "b">]><gpx/>')})
        self.assertEqual(bad.status_code, 400)

    def test_places_import_from_kml_gpx_takeout_json_and_csv(self):
        kml = b'<kml xmlns="http://www.opengis.net/kml/2.2"><Document><Placemark><name>Red Fort</name><Point><coordinates>77.2410,28.6562,0</coordinates></Point></Placemark></Document></kml>'
        wpt = b'<gpx xmlns="http://www.topografix.com/GPX/1/1"><wpt lat="28.6129" lon="77.2295"><name>India Gate</name></wpt></gpx>'
        takeout = json.dumps({"type": "FeatureCollection", "features": [{"geometry": {"coordinates": [77.1855, 28.5245]},
                              "properties": {"google_maps_url": "https://www.google.com/maps/place/x", "location": {"name": "Qutub Minar", "address": "Mehrauli"}}}]}).encode()
        listing = b"Title,Note,URL\nKarim's,Try the mutton,https://www.google.com/maps/place/y\n"
        for name, raw in (("trip.kml", kml), ("trip.gpx", wpt), ("Saved Places.json", takeout), ("Delhi.csv", listing)):
            self.assertEqual(self.client.post(self.url, {"operation": "places", "file": SimpleUploadedFile(name, raw)}).json()["result"]["added"], 1)
        places = self.client.get(self.url).json()["places"]
        self.assertEqual([p["name"] for p in places], ["Red Fort", "India Gate", "Qutub Minar", "Karim's"])
        self.assertEqual((places[0]["lat"], places[0]["lon"]), (28.6562, 77.241))
        self.assertEqual(places[3]["link"], "https://www.google.com/maps/place/y")
        again = self.client.post(self.url, {"operation": "places", "file": SimpleUploadedFile("trip.kml", kml)}).json()["result"]
        self.assertEqual(again, {"found": 1, "added": 0})
        self.assertEqual(self.client.post(self.url, {"operation": "places", "file": SimpleUploadedFile("x.txt", b"hi")}).status_code, 400)


GOOGLE_TRANSIT = {"routes": [{"duration": "2700s", "distanceMeters": 14200,
    "travelAdvisory": {"transitFare": {"currencyCode": "INR", "units": "40"}},
    "legs": [{"steps": [
        {"travelMode": "WALK", "staticDuration": "240s", "navigationInstruction": {"instructions": "Walk to Swargate"}},
        {"travelMode": "WALK", "staticDuration": "60s"},
        {"travelMode": "TRANSIT", "staticDuration": "1800s", "transitDetails": {
            "stopDetails": {"departureStop": {"name": "Swargate"}, "arrivalStop": {"name": "Shivajinagar"},
                            "departureTime": "2026-12-12T03:00:00Z", "arrivalTime": "2026-12-12T03:30:00Z"},
            "headsign": "Shivajinagar", "stopCount": 9,
            "transitLine": {"nameShort": "Line 1", "vehicle": {"name": {"text": "Metro"}}, "agencies": [{"name": "Pune Metro"}]}}}]}]},
    {"duration": "3600s", "distanceMeters": 5000, "legs": [{"steps": [{"travelMode": "WALK", "staticDuration": "3600s"}]}]}]}


class TravelLookupTests(TestCase):
    URL = "/api/mobility/travel-lookup/"

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("lookup-owner", password="pw-12345678"))

    def post(self, **body):
        return self.client.post(self.URL, body, content_type="application/json")

    def test_transit_lists_lines_stops_and_fare_and_skips_walk_only_routes(self):
        from apps.mobility.services.travel.providers import routing

        with patch.dict("os.environ", {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-key"}), \
                patch.object(routing, "request_json", return_value=(GOOGLE_TRANSIT, "h")) as call:
            data = self.post(operation="transit", origin="Swargate, Pune", destination="Shivajinagar, Pune").json()
        self.assertEqual(call.call_args.kwargs["json"]["travelMode"], "TRANSIT")
        self.assertEqual(len(data["routes"]), 1)
        route = data["routes"][0]
        self.assertEqual((route["minutes"], route["fare"]), (45, {"amount": "40.00", "currency": "INR"}))
        self.assertEqual(route["steps"][0], {"mode": "WALK", "minutes": 5, "note": "Walk to Swargate"})
        self.assertEqual((route["steps"][1]["line"], route["steps"][1]["vehicle"], route["steps"][1]["stops"]), ("Line 1", "Metro", 9))
        with patch.dict("os.environ", {"TRAVEL_GOOGLE_MAPS_API_KEY": ""}):
            self.assertIn("Google Maps key", self.post(operation="transit", origin="A street", destination="B street").json()["detail"])
        self.assertEqual(self.post(operation="transit", origin="A", destination="B", departure="2000-01-01T10:00").status_code, 400)

    def test_holidays_and_long_weekends_and_a_country_nager_does_not_cover(self):
        from apps.mobility.services.travel.providers import holidays

        replies = {"AvailableCountries": [{"countryCode": "US"}],
                   "PublicHolidays": [{"date": "2026-07-03", "localName": "Independence Day", "name": "Independence Day", "global": True}],
                   "LongWeekend": [{"startDate": "2026-07-03", "endDate": "2026-07-05", "dayCount": 3, "bridgeDays": []}]}
        fake = lambda method, url, **kw: (next(v for k, v in replies.items() if k in url), "h")
        with patch.object(holidays, "request_json", side_effect=fake):
            data = self.post(operation="holidays", country="us", year=2026).json()
            TravelProviderState.objects.update(next_allowed_at=None)  # the provider's 1-second pacing
            missing = self.post(operation="holidays", country="IN", year=2026)
        self.assertEqual(data["holidays"][0]["name"], "Independence Day")
        self.assertEqual(data["long_weekends"][0], {"start": "2026-07-03", "end": "2026-07-05", "days": 3, "leave_days": []})
        self.assertEqual(missing.status_code, 400)
        self.assertIn("no holidays for IN", missing.json()["detail"])
