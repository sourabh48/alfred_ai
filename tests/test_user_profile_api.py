import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase


class UserProfileApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="profile_user",
            password="Pass12345!",
            first_name="Sourabh",
            last_name="Sarkar",
            email="sourabh@example.com",
            monthly_income=125000,
            variable_income=15000,
            rent_or_emi=32000,
            city="Bengaluru",
            country="India",
        )
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.user.groups.add(Group.objects.create(name="profile-reviewers"))
        permission = Permission.objects.first()
        if permission:
            self.user.user_permissions.add(permission)
        self.client = Client()
        self.client.force_login(self.user)

    def test_profile_api_returns_only_safe_profile_fields(self):
        response = self.client.get("/api/users/profile/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(
            set(payload.keys()),
            {
                "id",
                "username",
                "first_name",
                "last_name",
                "email",
                "monthly_income",
                "variable_income",
                "rent_or_emi",
                "city",
                "country",
                "created_at",
            },
        )
        self.assertEqual(payload["username"], "profile_user")
        self.assertEqual(payload["email"], "sourabh@example.com")
        self.assertEqual(payload["monthly_income"], 125000.0)
        self.assertEqual(payload["variable_income"], 15000.0)
        self.assertEqual(payload["rent_or_emi"], 32000.0)
        self.assertEqual(payload["city"], "Bengaluru")
        self.assertEqual(payload["country"], "India")

    def test_profile_api_never_exposes_sensitive_auth_fields(self):
        response = self.client.get("/api/users/profile/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        for field in (
            "password",
            "is_staff",
            "is_superuser",
            "is_active",
            "groups",
            "user_permissions",
            "last_login",
            "date_joined",
        ):
            with self.subTest(field=field):
                self.assertNotIn(field, payload)

    def test_profile_api_allows_safe_profile_updates(self):
        response = self.client.patch(
            "/api/users/profile/",
            data=json.dumps(
                {
                    "first_name": "Updated",
                    "last_name": "User",
                    "email": "updated@example.com",
                    "monthly_income": 132000,
                    "variable_income": 25000,
                    "rent_or_emi": 41000,
                    "city": "Pune",
                    "country": "India",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.user.refresh_from_db()
        self.assertEqual(payload["first_name"], "Updated")
        self.assertEqual(payload["email"], "updated@example.com")
        self.assertEqual(payload["monthly_income"], 132000.0)
        self.assertEqual(self.user.city, "Pune")

    def test_profile_api_rejects_negative_money_values(self):
        response = self.client.patch(
            "/api/users/profile/",
            data=json.dumps({"monthly_income": -1}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.monthly_income, 125000)

    def test_profile_api_ignores_auth_sensitive_updates(self):
        response = self.client.patch(
            "/api/users/profile/",
            data=json.dumps(
                {
                    "username": "changed_username",
                    "is_superuser": True,
                    "is_staff": False,
                    "password": "new-password",
                    "email": "safe-change@example.com",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "profile_user")
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_staff)
        self.assertEqual(self.user.email, "safe-change@example.com")
