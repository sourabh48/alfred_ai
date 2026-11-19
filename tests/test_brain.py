"""The central brain keeps what ALFRED learns, encrypted per owner in the private vault (owner decision 2026-11-20)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ml_engine.services import brain
from apps.ml_engine.services.persistent_memory import MemoryStore
from apps.mobility.services.travel_conversation import new_session


class BrainTests(TestCase):
    def setUp(self):
        self.vault = Path(self.enterContext(TemporaryDirectory(prefix="alfred-brain-synthetic-"))) / "vault"
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.vault), ALFRED_TRAVEL_LOCAL_READING=True))
        self.alice = get_user_model().objects.create_user("synthetic-brain-alice")
        self.bob = get_user_model().objects.create_user("synthetic-brain-bob")

    def test_examples_are_encrypted_per_owner_bounded_and_cleared_by_a_reset(self):
        brain.remember(self.alice, "travel_reading", {"message": "me n the gang", "meant": {"travellers": 5}})
        self.assertEqual(brain.examples(self.alice, "travel_reading"), [{"message": "me n the gang", "meant": {"travellers": 5}}])
        self.assertEqual(brain.examples(self.bob, "travel_reading"), [])
        self.assertNotIn(b"the gang", (self.vault / "verified.sqlite3").read_bytes())
        with patch.object(brain, "PER_KIND", 2):
            for number in range(3):
                brain.remember(self.alice, "travel_reading", {"message": f"trip {number}", "meant": {"days": number + 1}})
        self.assertEqual([item["message"] for item in brain.examples(self.alice, "travel_reading")], ["trip 2", "trip 1"])
        with self.assertRaises(ValueError):
            brain.remember(self.alice, "anything", {"message": "x"})
        MemoryStore(self.vault).reset_owner(self.alice)
        self.assertEqual(brain.examples(self.alice, "travel_reading"), [])

    def test_fine_tuning_gets_only_this_owners_examples_as_chats(self):
        from scripts.brain_finetune import records
        brain.remember(self.alice, "travel_reading", {"message": "me n the gang", "meant": {"travellers": 5}})
        brain.remember(self.alice, "public_answer", {"question": "What is a dosa?", "answer": "A rice and lentil crepe."})
        brain.remember(self.bob, "public_answer", {"question": "Bob's question?", "answer": "Bob's answer."})
        chats = records(self.alice)
        self.assertEqual([chat["messages"][-1]["content"] for chat in chats], ['{"travellers": 5}', "A rice and lentil crepe."])
        self.assertEqual(chats[0]["messages"][1]["content"], '{"message": "me n the gang"}')
        self.assertNotIn("{today}", chats[0]["messages"][0]["content"])

    def test_a_correction_right_after_i_understood_teaches_the_reader(self):
        session = new_session(self.alice)
        self.client.force_login(self.alice)
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        with patch("apps.mobility.services.travel.understanding.read", return_value={"number_of_travelers": 3}):
            self.client.post(url, {"action": "message", "text": "me n the gang"}, content_type="application/json")
        with patch("apps.mobility.services.travel.understanding.read", return_value={}) as read:
            self.client.post(url, {"action": "message", "text": "no, we are 5 people"}, content_type="application/json")
        self.assertEqual(brain.examples(self.alice, "travel_reading"), [{"message": "me n the gang", "meant": {"travellers": 5}}])
        self.assertEqual(read.call_args.kwargs["lessons"], [])  # read before the correction was saved
        with patch("apps.mobility.services.travel.understanding.read", return_value={}) as read:
            self.client.post(url, {"action": "message", "text": "3 days"}, content_type="application/json")
        self.assertEqual(read.call_args.kwargs["lessons"], [{"message": "me n the gang", "meant": {"travellers": 5}}])
        self.assertEqual(len(brain.examples(self.alice, "travel_reading")), 1)  # an ordinary next answer is not a correction
