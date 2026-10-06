"""Password policy applies to user-facing writes, not existing-account login."""
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.test import TestCase
from django.urls import reverse


class PasswordSecurityTests(TestCase):
    def test_signup_rejects_weak_passwords_without_creating_or_logging_in_users(self):
        cases = (
            ({}, "qZ!4", "password_too_short"),
            ({}, "password", "password_too_common"),
            ({}, "918273645010", "password_entirely_numeric"),
            ({"username": "constellation2046"}, "constellation2046", "password_too_similar"),
            ({"email": "astronaut2046@example.com"}, "astronaut2046", "password_too_similar"),
            ({"first_name": "Constellation"}, "Constellation", "password_too_similar"),
            ({"last_name": "Constellation"}, "Constellation", "password_too_similar"),
        )
        for index, (identity, password, code) in enumerate(cases):
            with self.subTest(code=code, attributes=tuple(identity)):
                self.client.logout()
                data = {"username": f"policy_candidate_{index}", **identity,
                        "password1": password, "password2": password}
                response = self.client.post("/signup/", data)
                self.assertEqual(response.status_code, 200)
                errors = response.context["form"].errors.as_data()["password2"]
                self.assertIn(code, [error.code for error in errors])
                self.assertFalse(get_user_model().objects.filter(username=data["username"]).exists())
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_existing_weak_password_still_authenticates(self):
        user = get_user_model().objects.create_user(username="existing_policy_user", password="weak")
        original_hash = user.password
        response = self.client.post("/login/", {"username": user.username, "password": "weak"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))
        user.refresh_from_db()
        self.assertEqual(user.password, original_hash)

    def test_password_change_rejects_weak_replacement_and_preserves_hash(self):
        user = get_user_model().objects.create_user(username="existing_policy_user", password="weak")
        original_hash = user.password
        form = PasswordChangeForm(user, {"old_password": "weak",
                                       "new_password1": user.username,
                                       "new_password2": user.username})
        self.assertFalse(form.is_valid())
        self.assertIn("password_too_similar", [error.code for error in form.errors.as_data()["new_password2"]])
        user.refresh_from_db()
        self.assertEqual(user.password, original_hash)

    def test_admin_password_change_rejects_weak_replacement(self):
        admin = get_user_model().objects.create_superuser(
            username="policy_admin", email="admin@example.com", password="Existing-X7!Nebula")
        user = get_user_model().objects.create_user(username="policy_subject", password="Old-X8!Nebula")
        original_hash = user.password
        self.client.force_login(admin)
        response = self.client.post(reverse("admin:auth_user_password_change", args=[user.pk]),
                                    {"password1": "password", "password2": "password", "usable_password": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This password is too common.")
        user.refresh_from_db()
        self.assertEqual(user.password, original_hash)

    def test_admin_password_change_accepts_and_hashes_valid_replacement(self):
        admin = get_user_model().objects.create_superuser(
            username="policy_admin", email="admin@example.com", password="Existing-X7!Nebula")
        user = get_user_model().objects.create_user(username="policy_subject", password="Old-X8!Nebula")
        self.client.force_login(admin)
        password = "Orbit-Q9!Unrelated-Lantern"
        response = self.client.post(reverse("admin:auth_user_password_change", args=[user.pk]),
                                    {"password1": password, "password2": password, "usable_password": "true"})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password(password))
        self.assertNotEqual(user.password, password)
