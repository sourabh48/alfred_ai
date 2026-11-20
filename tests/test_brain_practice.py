"""A Gemini practice set keeps only examples the travel reader's own checks accept (owner choice 2026-11-20)."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alfred_ai.services.public_http import PublicHTTPError
from apps.ml_engine.services import brain, brain_practice

TODAY = date(2026, 11, 20)


class PracticeTests(TestCase):
    def setUp(self):
        vault = Path(self.enterContext(TemporaryDirectory(prefix="alfred-practice-synthetic-"))) / "vault"
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(vault)))
        self.enterContext(patch("django.utils.timezone.localdate", return_value=TODAY))
        self.owner = get_user_model().objects.create_user("synthetic-practice-owner")

    def test_only_examples_whose_every_field_the_message_supports_are_kept(self):
        good = {"message": "me n 3 frnds goa  24-27 dec by train 20k total",
                "meant": {"destination": "Goa", "travellers": 4, "start_date": "2026-12-24", "end_date": "2026-12-27", "days": 4,
                          "transport": "train", "budget_rupees": 20000, "budget_scope": "whole_trip", "food": None}}
        self.assertEqual(brain_practice.usable(good)["meant"], {key: value for key, value in good["meant"].items() if value})
        bad = [{"message": "goa trip", "meant": {"destination": "Manali"}},  # a place the message never names
               {"message": "goa 24-27 dec", "meant": {"destination": "Goa", "start_date": "2026-12-24", "end_date": "2026-12-27",
                                                      "days": 3}},  # days disagree with the dates
               {"message": "goa for chill", "meant": {"destination": "Goa", "trip_styles": ["partying"]}},
               {"message": "goa", "meant": {"destination": "Goa", "budget_scope": "per_person"}},  # a scope without a budget
               {"message": "nandi hills ride this sunday", "meant": {"destination": "nandi hills", "transport": "ride"}},
               {"message": "", "meant": {}}, "not an object"]
        self.assertEqual([brain_practice.usable(item) for item in bad], [None] * len(bad))

    def test_generation_keeps_new_examples_holds_back_a_tenth_and_stops_on_quota(self):
        batches = [[{"message": f"goa with {n} frnds", "meant": {"destination": "Goa", "travellers": n + 1}} for n in range(2, 14)]
                   + [{"message": "goa with 2 frnds", "meant": {"destination": "Goa", "travellers": 3}},  # a repeat
                      {"message": "kerala", "meant": {"destination": "Goa"}}]]
        sent = []

        def ask(key, theme, count, today, *, deadline):
            sent.append((key, theme, today))
            if len(sent) == 1:
                raise PublicHTTPError("api_error")  # one busy moment is skipped
            if batches:
                return batches.pop()
            raise PublicHTTPError("quota_exhausted")
        result = brain_practice.generate(self.owner, 30, key="synthetic-key", ask=ask)
        self.assertEqual(result, {"kept": 12, "asked": 14, "rejected": 1, "stopped": "quota_exhausted"})
        self.assertEqual(sent[1], ("synthetic-key", brain_practice.THEMES[1], TODAY))
        kept = brain.examples(self.owner, "travel_practice")
        self.assertEqual(len(kept), 12)
        self.assertEqual(sum(item["held_back"] for item in kept), 1)
        self.assertEqual(brain.examples(self.owner, "travel_reading"), [])  # practice is never fed back as a correction
