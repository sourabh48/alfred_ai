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
