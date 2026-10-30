"""FAMILY-05 synthetic contracts: alignment never scores missing evidence as favorable or fragile."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.relationship.models import RelationshipProfile
from apps.relationship.serializers import RelationshipProfileSerializer
from apps.relationship.services.relationship_intelligence import build_relationship_alignment


SERVICE = "apps.relationship.services.relationship_intelligence"


def planning(inflation=5.0, vix=12.0):
    return {"payload": {"inflation": {"latest_value": inflation}, "market": {"india_vix": vix}},
            "evidence": [], "freshness": {}, "notes": []}


class RelationshipCoverageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("relationship_cover", password="synthetic-pass-123")
        self.profile = RelationshipProfile.objects.create(
            user=self.user, partner_name="Synthetic", partner_financial_score=70, partner_savings_habits=3, compatibility_score=75)

    def set_income(self):
        self.user.monthly_income = Decimal("100000.00"); self.user.save(update_fields=["monthly_income"])

    def alignment(self, context=None, model=None):
        with patch(f"{SERVICE}.verified_intelligence.household_planning_context", return_value=context or planning()), \
                patch(f"{SERVICE}.relationship_model_predictor.predict_score", return_value=model):
            return build_relationship_alignment(self.user).payload

    def test_complete_inputs_keep_the_existing_weighted_formula(self):
        self.set_income()
        payload = self.alignment()
        factors = {item["label"]: item["score"] for item in payload["factors"]}
        expected = round(factors["Financial Alignment"]*.32 + factors["Savings Habit Fit"]*.23
                         + factors["Shared Resilience"]*.3 + factors["Planning Pressure"]*.15, 2)
        self.assertAlmostEqual(payload["alignment_score"], expected, places=1)
        self.assertEqual(payload["coverage"], {"status": "observed", "missing_inputs": []})

    def test_missing_income_abstains_instead_of_calling_savings_thin(self):
        payload = self.alignment()
        self.assertEqual((payload["compatibility"], payload["alignment_score"]), ("Unknown", 0))
        self.assertEqual(payload["coverage"]["status"], "insufficient_data")
        self.assertIn("Your income", payload["coverage"]["missing_inputs"])
        self.assertFalse(any("Savings runway is thin" in line for line in payload["insights"]))
        self.assertIn("income", payload["message"].lower())

    def test_missing_external_context_is_not_a_perfect_planning_score(self):
        self.set_income()
        complete = self.alignment()
        payload = self.alignment(context=planning(None, None))
        self.assertNotIn("Planning Pressure", [item["label"] for item in payload["factors"]])
        self.assertEqual(payload["coverage"]["status"], "partial")
        self.assertIn("External planning context", payload["coverage"]["missing_inputs"])
        self.assertFalse(any("Shared planning pressure" in line for line in payload["insights"]))
        self.assertLess(payload["alignment_score"], complete["alignment_score"] + 15)

    def test_unset_partner_inputs_are_not_measured_zero(self):
        self.set_income()
        RelationshipProfile.objects.filter(pk=self.profile.pk).update(partner_financial_score=0, compatibility_score=0)
        payload = self.alignment()
        labels = [item["label"] for item in payload["factors"]]
        self.assertNotIn("Financial Alignment", labels)
        self.assertNotIn("Shared Resilience", labels)
        self.assertIn("Partner financial score", payload["coverage"]["missing_inputs"])
        self.assertIn("Compatibility input", payload["coverage"]["missing_inputs"])
        self.assertFalse(any("Partner financial score is 0" in line for line in payload["insights"]))

    def test_model_blend_needs_complete_inputs(self):
        self.set_income()
        base = self.alignment(context=planning(None, None))
        self.assertEqual(self.alignment(context=planning(None, None), model=99.0)["alignment_score"], base["alignment_score"])
        complete = self.alignment()
        self.assertGreater(self.alignment(model=99.0)["alignment_score"], complete["alignment_score"])

    def test_payload_states_it_is_not_a_compatibility_prediction(self):
        self.set_income()
        notes = " ".join(self.alignment()["grounding"]["notes"])
        self.assertIn("not a prediction", notes)


class RelationshipValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("relationship_valid", password="synthetic-pass-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def payload(self, **changes):
        return {"partner_name": "Synthetic", "partner_financial_score": 70, "partner_savings_habits": 3,
                "compatibility_score": 75, **changes}

    def test_out_of_range_and_non_finite_inputs_are_rejected(self):
        for field, value in (("partner_financial_score", -1), ("partner_financial_score", 101),
                             ("partner_financial_score", "NaN"), ("partner_financial_score", "Infinity"),
                             ("compatibility_score", 1000), ("compatibility_score", "NaN"),
                             ("partner_savings_habits", 0), ("partner_savings_habits", 6)):
            with self.subTest(field=field, value=value):
                response = self.client.post("/api/relationship/", self.payload(**{field: value}), format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json().get("details", response.json()) or {})
        self.assertFalse(RelationshipProfile.objects.exists())

    def test_boundaries_are_accepted_and_owner_is_server_assigned(self):
        other = get_user_model().objects.create_user("relationship_other", password="synthetic-pass-123")
        response = self.client.post("/api/relationship/", self.payload(
            partner_financial_score=100, compatibility_score=0, partner_savings_habits=5, user=other.pk), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RelationshipProfile.objects.get().user, self.user)

    def test_legacy_out_of_range_record_stays_readable_and_is_not_rewritten(self):
        row = RelationshipProfile.objects.create(user=self.user, partner_name="Legacy", partner_financial_score=500,
                                                 partner_savings_habits=9, compatibility_score=300)
        self.assertEqual(RelationshipProfileSerializer(row).data["partner_financial_score"], 500)
        response = self.client.patch(f"/api/relationship/{row.pk}/", {"partner_name": "Renamed"}, format="json")
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual((row.partner_name, row.partner_financial_score, row.partner_savings_habits), ("Renamed", 500, 9))
