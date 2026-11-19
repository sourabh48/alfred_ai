"""Phone sync to Google Calendar and Tasks: connect asks only for the app-created calendar and Tasks, the token is kept
encrypted, sync writes only what changed, never sends amounts, and disconnect revokes. Google is faked; no network."""
import json
import os
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services import google_sync, social_login
from apps.investments.models import ResearchDecision
from apps.mobility.models import TravelPlan
from apps.mobility.services.travel import trip_tools

KEYS = {"ALFRED_GOOGLE_CLIENT_ID": "x-google-id", "ALFRED_GOOGLE_CLIENT_SECRET": "x-google-secret"}


class Google:
    """Token, userinfo, Calendar and Tasks endpoints, recording every call."""
    def __init__(self, scope=None):
        self.scope = scope if scope is not None else f"openid email {google_sync.SCOPES}"
        self.calls, self.next_id = [], 0

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        status, body = 200, {}
        if url == social_login.PROVIDERS["google"][2] or url == google_sync.TOKEN_URL:
            body = {"access_token": "short-lived", "refresh_token": "lasting-secret", "scope": self.scope}
        elif "holiday%40group" in url:
            if "en.in%23" in url:
                status = 404  # the two-letter name is missing, the older name answers
            else:
                body = {"items": [{"summary": "Republic Day", "description": "Public holiday", "start": {"date": "2027-01-26"}},
                                  {"summary": "Holi", "description": "Restricted holiday", "start": {"date": "2027-03-22"}},
                                  {"summary": "Independence Day", "description": "Public holiday", "start": {"date": "2027-08-13"}}]}
        elif "openidconnect" in url:
            body = {"sub": "g-1", "email": "owner@example.org", "email_verified": True}
        elif method == "POST":
            self.next_id += 1
            body = {"id": f"id-{self.next_id}"}
        elif method == "DELETE":
            status = 204
        return SimpleNamespace(status=status, json=lambda: body)

    def writes(self):
        return [(m, u.rsplit("/", 1)[-1] if m != "POST" else u) for m, u, _ in self.calls if m in ("POST", "PUT", "DELETE")
                and "googleapis.com/token" not in u and "oauth2" not in u]


class ConnectedGoogle(TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        for env in (KEYS, {"ALFRED_DATA_DIR": folder.name}):
            p = patch.dict(os.environ, env)
            p.start()
            self.addCleanup(p.stop)
        self.owner = get_user_model().objects.create_user("sync-owner", email="owner@example.org", password="pw-12345678")
        # With sign-in set up, everyone signed in has a provider-verified email (owner decision 2026-11-19).
        self.owner.email_identities.create(provider="google", subject="g-1", email="owner@example.org")
        self.client.force_login(self.owner)

    def connect(self, google=None):
        google = google or Google()
        start = self.client.get("/auth/google/start/?purpose=sync")
        query = parse_qs(urlsplit(start["Location"]).query)
        with patch.object(social_login.public_http, "request", google):
            response = self.client.get("/auth/google/callback/", {"code": "c", "state": query["state"][0]})
        return query, response


class GoogleSyncTests(ConnectedGoogle):
    def test_connect_asks_for_offline_calendar_and_tasks_and_keeps_the_token_encrypted(self):
        query, response = self.connect()
        self.assertEqual(response["Location"], "/settings/#settingsGoogleSync")
        self.assertEqual(query["access_type"], ["offline"])
        self.assertIn("auth/calendar.app.created", query["scope"][0])
        self.assertNotIn("auth/calendar ", query["scope"][0] + " ")  # never the full calendar permission
        stored = google_sync._path(self.owner).read_text(encoding="utf-8")
        self.assertNotIn("lasting-secret", stored)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.owner.pk)
        status = self.client.get("/api/settings/google-sync/").json()
        self.assertEqual((status["connected"], status["account"]), (True, "owner@example.org"))

    def test_without_both_permissions_nothing_is_stored(self):
        self.connect(Google(scope="openid email https://www.googleapis.com/auth/tasks"))
        data = self.client.get("/api/settings/google-sync/").json()
        self.assertFalse(data["connected"])
        self.assertIn("Tick both", data["error"])

    def test_sync_writes_events_and_tasks_once_then_only_changes_and_never_amounts(self):
        self.connect()
        today = timezone.localdate()
        plan = TravelPlan.objects.create(user=self.owner, title="Goa", destination="Goa", status="planned",
                                         start_date=today + timedelta(days=10), end_date=today + timedelta(days=12),
                                         planning_state={"_packing_checklist": {"revision": 1, "items": [{"id": "p1", "label": "Sunscreen", "packed": False}]}})
        trip_tools.add_booking(self.owner, plan, {"kind": "flight", "title": "6E 501", "confirmation": "QX7P2L",
                                                  "start": f"{plan.start_date}T07:45", "amount": "6420", "currency": "INR"})
        ResearchDecision.objects.create(user=self.owner, instrument="Synthetic Ltd", rating="hold", thesis="t", decided_on=today,
                                        review_on=today + timedelta(days=30), entry_price=Decimal("10"))
        google = Google()
        with patch.object(google_sync.public_http, "request", google):
            result = self.client.post("/api/settings/google-sync/", {"action": "sync"}, content_type="application/json").json()
        self.assertEqual((result["events"], result["tasks"]), (3, 1))
        bodies = json.dumps([kw.get("json_body") for _, _, kw in google.calls])
        self.assertIn("Confirmation QX7P2L", bodies)
        self.assertNotIn("6420", bodies)
        self.assertIn('"timeZone"', bodies)
        self.assertEqual(sum(1 for m, u in google.writes() if m == "POST"), 6)  # calendar, list, 3 events, 1 task

        again = Google()
        with patch.object(google_sync.public_http, "request", again):
            google_sync.sync(self.owner)
        self.assertEqual(again.writes(), [])  # nothing changed, nothing written

        plan.title = "Goa with friends"
        plan.save()
        trip_tools.remove_booking(self.owner, plan, trip_tools.state(self.owner, plan)["bookings"][0]["id"])
        changed = Google()
        with patch.object(google_sync.public_http, "request", changed):
            google_sync.sync(self.owner)
        self.assertEqual(sorted(m for m, _ in changed.writes()), ["DELETE", "PUT", "PUT"])  # trip event, packing note, booking gone

    def test_disconnect_revokes_and_forgets_the_token(self):
        self.connect()
        google = Google()
        with patch.object(google_sync.public_http, "request", google):
            data = self.client.post("/api/settings/google-sync/", {"action": "disconnect"}, content_type="application/json").json()
        self.assertFalse(data["connected"])
        self.assertEqual(google.calls[0][1], google_sync.REVOKE_URL)
        self.assertEqual(google.calls[0][2]["data"]["token"], "lasting-secret")
        self.assertFalse(Path(google_sync._path(self.owner)).exists())


class GoogleHolidayTests(ConnectedGoogle):
    """India is missing from Nager.Date, so its public holidays come from Google's holiday calendar (owner, 2026-11-19)."""

    def test_country_missing_from_nager_reads_google_holiday_calendar_with_long_weekends(self):
        from apps.mobility.services.travel.providers.base import ProviderResult
        self.connect()
        missing = ProviderResult("nager_date", "holidays", success=False, error="country_not_covered")
        google = Google()
        with patch("apps.mobility.services.travel.cache.query", return_value=missing), patch.object(google_sync.public_http, "request", google):
            data = self.client.post("/api/mobility/travel-lookup/", {"operation": "holidays", "country": "IN", "year": 2027},
                                    content_type="application/json").json()
        self.assertEqual([h["name"] for h in data["holidays"]], ["Republic Day", "Holi", "Independence Day"])
        self.assertEqual([h["national"] for h in data["holidays"]], [True, False, True])
        self.assertEqual(data["holidays"][1]["kind"], "Restricted holiday")
        self.assertEqual(data["attribution"], "Holidays from Google Calendar")
        # Tuesday 26 Jan: Saturday to Tuesday with Monday as leave; Friday 13 Aug: Friday to Sunday.
        self.assertEqual(data["long_weekends"], [{"start": "2027-01-23", "end": "2027-01-26", "days": 4, "leave_days": ["2027-01-25"]},
                                                 {"start": "2027-08-13", "end": "2027-08-15", "days": 3, "leave_days": []}])
        reads = [u for m, u, _ in google.calls if m == "GET" and "holiday" in u]
        self.assertEqual(len(reads), 2)
        self.assertIn("en.indian%23holiday", reads[1])
        self.assertTrue(all(kw.get("json_body") is None for m, u, kw in google.calls if "holiday" in u))  # only the country leaves

    def test_without_the_public_calendar_permission_sync_still_connects_and_holidays_say_how_to_get_them(self):
        self.connect(Google(scope=f"openid email {google_sync.REQUIRED}"))
        self.assertEqual(self.client.get("/api/settings/google-sync/").json()["holidays"], False)
        with self.assertRaisesRegex(google_sync.SyncError, "Connect Google"):
            google_sync.public_holidays(self.owner, "IN", 2027)
