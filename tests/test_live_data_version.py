from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services.live_version import data_version, request_method
from apps.behavioral.models import BehavioralSignal
from apps.family.models import Dependent, FamilyAccountLink

URL = "/api/session/data-version/"


class LiveDataVersionTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.owner = User.objects.create_user(username="version_owner", password="synthetic-pass-1")
        self.other = User.objects.create_user(username="version_other", password="synthetic-pass-1")
        self.client.force_login(self.owner)

    def version(self):
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        return response.json()["version"]

    def test_requires_login(self):
        self.client.logout()
        self.assertNotEqual(self.client.get(URL).status_code, 200)

    def test_idle_reads_keep_the_version(self):
        first = self.version()
        self.client.get("/api/family/")
        self.assertEqual(self.version(), first)

    def test_api_write_changes_the_version(self):
        first = self.version()
        response = self.client.post("/api/family/", {"name": "Synthetic", "age": 7, "relation": "child"},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(self.version(), first)

    def test_session_ping_does_not_change_the_version(self):
        first = self.version()
        self.assertEqual(self.client.post("/api/session/ping/").status_code, 200)
        self.assertEqual(self.version(), first)

    def test_client_error_log_does_not_change_the_version(self):
        from apps.reports.models import OperationalLog

        first = self.version()
        response = self.client.post("/api/operational/logs/client/", {"message": "Synthetic panel failure"},
                                    content_type="application/json")
        self.assertLess(response.status_code, 300)
        self.assertTrue(OperationalLog.objects.filter(user=self.owner).exists())
        self.assertEqual(self.version(), first)

    def test_bulk_update_through_the_api_changes_the_version(self):
        from django.test import RequestFactory
        from django.http import JsonResponse
        from alfred_ai.middleware import UserDataCacheMiddleware

        dependent = Dependent.objects.create(user=self.owner, name="Bulk", age=8, relation="child")
        first = self.version()

        def view(request):  # .update() sends no model signals; only the SQL watcher sees it.
            Dependent.objects.filter(pk=dependent.pk).update(age=9)
            return JsonResponse({})

        request = RequestFactory().post("/api/family/bulk/")
        request.user = self.owner
        UserDataCacheMiddleware(view)(request)
        self.assertNotEqual(self.version(), first)

    def test_background_save_changes_the_version_but_page_load_writes_do_not(self):
        first = self.version()
        token = request_method.set("GET")
        try:
            Dependent.objects.create(user=self.owner, name="Logged on read", age=3, relation="child")
        finally:
            request_method.reset(token)
        self.assertEqual(self.version(), first)
        # No request at all: a Huey job or import.
        Dependent.objects.create(user=self.owner, name="Imported", age=4, relation="child")
        self.assertNotEqual(self.version(), first)

    def test_other_accounts_change_the_version_only_when_shared(self):
        first = data_version(self.owner)
        Dependent.objects.create(user=self.other, name="Not shared", age=5, relation="child")
        self.assertEqual(data_version(self.owner), first)
        FamilyAccountLink.objects.create(created_by=self.owner, linked_user=self.other, invite_code_hash="h" * 64, expires_at=timezone.now() + timedelta(days=1),
                                         status=FamilyAccountLink.STATUS_ACCEPTED,
                                         linked_user_share_financial_summary=True)
        shared = data_version(self.owner)
        # A linked account's private records and activity stay invisible.
        BehavioralSignal.objects.create(user=self.other, stress_score=1)
        self.assertEqual(data_version(self.owner), shared)
        Dependent.objects.create(user=self.other, name="Shared", age=6, relation="child")
        self.assertNotEqual(data_version(self.owner), shared)
