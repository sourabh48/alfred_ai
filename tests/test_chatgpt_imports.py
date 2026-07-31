import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.reports.models import ChatGPTImport


class ChatGPTImportTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="chat_import_user", password="Pass12345!")
        self.other_user = user_model.objects.create_user(username="other_chat_import_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_pasted_chat_transcript_is_stored_as_reviewable_context(self):
        transcript = """
        User: My ChatGPT dashboard tracks a Honda Activa vehicle service bill, route wear, mileage and official catalog model selection.
        Assistant: Keep vehicle maintenance actions separate from career salary and recruiter evidence until reviewed.
        User: Also import resume, job salary, compensation benchmark and CIBIL credit report notes.
        """

        response = self.client.post(
            "/api/reports/chatgpt-imports/",
            data=json.dumps(
                {
                    "title": "",
                    "source_label": "ChatGPT dashboard",
                    "import_type": "mixed_context",
                    "raw_text": transcript,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertNotIn("raw_text", payload)
        self.assertEqual(payload["source_label"], "ChatGPT dashboard")
        self.assertEqual(payload["import_type"], "mixed_context")
        self.assertEqual(payload["status"], "review_ready")
        self.assertGreaterEqual(payload["parsed_payload"]["message_count"], 3)

        modules = {item["module"] for item in payload["detected_modules"]}
        self.assertIn("mobility", modules)
        self.assertIn("career", modules)
        self.assertIn("credit", modules)

        import_record = ChatGPTImport.objects.get(user=self.user)
        self.assertIn("Honda Activa", import_record.raw_text)
        self.assertEqual(import_record.content_hash, payload["content_hash"])

    def test_chatgpt_json_export_mapping_is_normalized(self):
        export_payload = {
            "title": "Existing ALFRED dashboard",
            "mapping": {
                "node-1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Vehicle catalog maintenance depth and service-cost route wear need review."]},
                    }
                },
                "node-2": {
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Resume salary benchmark and live job feed evidence are still in progress."]},
                    }
                },
            },
        }

        response = self.client.post(
            "/api/reports/chatgpt-imports/",
            data=json.dumps({"raw_text": json.dumps(export_payload), "import_type": "dashboard_export"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["title"], "Existing ALFRED dashboard")
        self.assertEqual(payload["parsed_payload"]["source_kind"], "chatgpt_json_export")
        self.assertEqual(payload["parsed_payload"]["role_counts"]["assistant"], 1)
        self.assertEqual(payload["parsed_payload"]["role_counts"]["user"], 1)

    def test_import_list_is_user_scoped(self):
        ChatGPTImport.objects.create(
            user=self.other_user,
            title="Other user context",
            raw_text="Other private dashboard",
            parsed_payload={"preview": "Other private dashboard"},
        )
        ChatGPTImport.objects.create(
            user=self.user,
            title="My context",
            raw_text="My vehicle dashboard",
            parsed_payload={"preview": "My vehicle dashboard"},
        )

        response = self.client.get("/api/reports/chatgpt-imports/")

        self.assertEqual(response.status_code, 200)
        titles = [item["title"] for item in response.json()]
        self.assertEqual(titles, ["My context"])

    def test_empty_chat_import_is_rejected(self):
        response = self.client.post(
            "/api/reports/chatgpt-imports/",
            data=json.dumps({"raw_text": "   "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
