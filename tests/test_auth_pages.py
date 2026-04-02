from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings


class AuthPageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_signin_alias_redirects_to_login(self):
        response = self.client.get("/signin/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login/")

    def test_login_page_renders(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to Alfred")
        self.assertContains(response, "Create account")

    def test_signup_page_renders(self):
        response = self.client.get("/signup/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your Alfred account")
        self.assertContains(response, "Sign in")

    @override_settings(DEBUG=False)
    def test_not_found_page_offers_route_back_home(self):
        response = self.client.get("/missing-workspace/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "That page does not exist in Alfred.", status_code=404)
        self.assertContains(response, "Go to Home", status_code=404)

    def test_signup_creates_user_and_redirects_to_dashboard(self):
        response = self.client.post(
            "/signup/",
            data={
                "username": "new_user",
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "User",
                "city": "Bengaluru",
                "country": "India",
                "monthly_income": "85000",
                "variable_income": "5000",
                "rent_or_emi": "22000",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard/")

        user = get_user_model().objects.get(username="new_user")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.city, "Bengaluru")
        self.assertEqual(user.monthly_income, 85000)
