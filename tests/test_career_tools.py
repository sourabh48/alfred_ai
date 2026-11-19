"""More Career Ops modes (career-ops fe9cb888, MIT): profile, GitHub, discover, gambit, retro, reply watch. Synthetic, no network."""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from alfred_ai.services.public_http import PublicHTTPError
from apps.career.models import CareerJobAnalysis, CareerResume
from apps.career.services import career_tools
from tests.test_career_application_kit import CV

URL = "/api/career/tools/"


def _reply(payload):
    return type("Reply", (), {"json": lambda self: payload})()


class FakeReasoner:
    model = "synthetic-local"

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def reason(self, payload, *, max_output_tokens, deadline):
        self.calls.append(payload)
        return self.replies.pop(0)


class CareerToolsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = get_user_model().objects.create_user("synthetic-career-owner", password="Test12345!")
        self.other = get_user_model().objects.create_user("synthetic-career-other", password="Test12345!")
        self.resume = CareerResume.objects.create(
            user=self.owner, uploaded_file=SimpleUploadedFile("cv.txt", b"cv"), file_name="cv.txt", parser_status="parsed",
            extracted_text=CV, extracted_payload={"role": "Backend Engineer", "experience_years": 5, "skills": ["Python", "Django"],
                                                  "links": ["https://github.com/asha-synthetic"]})
        self.client.force_login(self.owner)

    def post(self, **body):
        return self.client.post(URL, body, content_type="application/json")

    def test_master_profile_keeps_only_cv_lines_the_owner_confirms(self):
        state = self.client.get(URL).json()
        self.assertEqual(state["github"], "asha-synthetic")
        new = state["profile"]["new"]
        result = next(f for f in new if f["text"] == "Reduced SQL query time by 40% with indexing")
        python = next(f for f in new if f["kind"] == "skill" and f["text"] == "Python")
        self.assertEqual(result["source"], "Your CV, as written")
        self.assertTrue(all(f["text"] in CV or f["kind"] in ("skill", "link") for f in new))  # copied, never rewritten
        state = self.post(operation="profile_save", keep=[result["id"]], drop=[python["id"]]).json()
        self.assertEqual([f["id"] for f in state["profile"]["facts"]], [result["id"]])
        self.assertNotIn(python["id"], [f["id"] for f in state["profile"]["new"]])  # dropped stays dropped
        self.assertNotIn(result["id"], [f["id"] for f in state["profile"]["new"]])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(URL).json()["profile"]["facts"], [])  # owner isolation

    def test_github_adds_only_what_the_cv_lacks_after_confirmation(self):
        repos = [{"name": "ledger-sync", "description": "Bank CSV importer", "language": "Go", "topics": ["kafka", "python"],
                  "html_url": "https://github.com/asha-synthetic/ledger-sync", "fork": False},
                 {"name": "someone-else", "description": "Fork", "language": "Rust", "fork": True, "html_url": "https://github.com/x/y"}]
        with patch.object(career_tools.public_http, "request", return_value=_reply(repos)) as request:
            found = self.post(operation="github", username="asha-synthetic").json()["result"]["suggestions"]
            self.assertEqual(request.call_args.args[1], "https://api.github.com/users/asha-synthetic/repos")
            self.assertEqual([(f["kind"], f["text"]) for f in found],
                             [("skill", "Go"), ("skill", "kafka"), ("project", "ledger-sync: Bank CSV importer")])  # Python is in the CV
            go = found[0]["id"]
            state = self.post(operation="profile_save", keep=[go], drop=[], username="asha-synthetic").json()
        self.assertEqual(state["profile"]["facts"][0]["source"], "Used in https://github.com/asha-synthetic/ledger-sync")
        self.assertEqual(self.post(operation="github", username="bad name!").status_code, 400)

    def test_discover_finds_public_boards_and_lists_matching_roles(self):
        def reply(method, url, **kwargs):
            if url == "https://boards-api.greenhouse.io/v1/boards/syntheticpay/jobs":
                return _reply({"jobs": [{"title": "Senior Backend Engineer", "absolute_url": "https://boards.greenhouse.io/syntheticpay/jobs/1",
                                         "location": {"name": "Pune"}},
                                        {"title": "Office Manager", "absolute_url": "https://boards.greenhouse.io/syntheticpay/jobs/2"}]})
            raise PublicHTTPError("upstream_status")

        with patch.object(career_tools.public_http, "request", side_effect=reply):
            added = self.post(operation="companies_add", names="SyntheticPay Technologies, Nowhere Ltd").json()
            self.assertEqual([(r["name"], r["board"]) for r in added["result"]["results"]],
                             [("SyntheticPay Technologies", "Greenhouse"), ("Nowhere Ltd", None)])
            self.assertEqual([c["name"] for c in added["companies"]], ["SyntheticPay Technologies"])
            self.client.get("/api/career/triage-brief/")
            career_tools._save(self.owner, career_tools.BRIEF, "brief", {"brief": {"target_roles": ["Backend Engineer"]}})
            roles = self.post(operation="open_roles").json()["result"]
        self.assertEqual([(r["title"], r["company"]) for r in roles["roles"]], [("Senior Backend Engineer", "SyntheticPay Technologies")])
        self.assertEqual(career_tools.slugs("SyntheticPay Technologies Pvt Ltd"), ["syntheticpay"])
        self.assertEqual(self.post(operation="company_remove", name="syntheticpay technologies").json()["companies"], [])

    def test_gambit_drops_invented_numbers_and_saves_nothing(self):
        answer = ('{"title": "Payments Reliability Engineer", "why_they_need_it": ["Checkout failures hurt sales.", "Outages cost 9 crore."], '
                  '"responsibilities": ["Own the Django payment APIs.", "Cut SQL query time by 40% again."], '
                  '"requirements": ["Python and Django."], "pitch": "I built Django APIs serving 2 million requests a day. Guaranteed results."}')
        with patch.object(career_tools, "_reasoner", return_value=FakeReasoner([answer])):
            g = self.post(operation="gambit", company="SyntheticPay", notes="Their checkout keeps failing at peak hours and they hire no SRE.").json()["result"]
        self.assertEqual(g["why_they_need_it"], ["Checkout failures hurt sales."])  # 9 crore was never given
        self.assertEqual(g["responsibilities"], ["Own the Django payment APIs.", "Cut SQL query time by 40% again."])  # 40% is in the CV
        self.assertEqual(g["pitch"], "I built Django APIs serving 2 million requests a day.")
        self.assertIn("(no job posting; your own pitch)", g["posting"])
        self.assertEqual(CareerJobAnalysis.objects.count(), 0)
        self.assertEqual(self.post(operation="gambit", company="X", notes="too short").status_code, 400)

    def test_retro_applies_only_ticked_rules_the_owner_actually_wrote(self):
        words = "Stop suggesting jobs in Bangalore. I want Data Engineer roles. My floor is 2500000 INR."
        reply = ('{"rules": [{"field": "locations", "action": "remove", "value": "Bangalore", "why": "You said stop."},'
                 '{"field": "target_roles", "action": "add", "value": "Data Engineer"},'
                 '{"field": "pay_floor", "action": "set", "value": "2,500,000", "currency": "INR"},'
                 '{"field": "target_roles", "action": "add", "value": "CTO"},'
                 '{"field": "salary_history", "action": "add", "value": "jobs"}]}')
        with patch.object(career_tools, "_reasoner", return_value=FakeReasoner([reply])):
            rules = self.post(operation="retro", corrections=words).json()["result"]["rules"]
        self.assertEqual([(r["field"], r["value"]) for r in rules],
                         [("locations", "Bangalore"), ("target_roles", "Data Engineer"), ("pay_floor", "2500000")])  # CTO was never said
        applied = self.post(operation="retro_apply", corrections=words, rules=rules[1:]).json()
        self.assertEqual(applied["result"]["applied"], 2)
        brief = self.client.get("/api/career/triage-brief/").json()["brief"]
        self.assertEqual((brief["target_roles"], brief["pay_floor"], brief["pay_currency"]), (["Data Engineer"], "2500000.00", "INR"))
        forged = [{"field": "target_roles", "action": "add", "value": "CTO"}]
        self.assertEqual(self.post(operation="retro_apply", corrections=words, rules=forged).status_code, 400)


class FakeGmail:
    """A synthetic Gmail inbox behind a fake transport; records every call so the test can prove it only read."""

    def __init__(self, inbox):
        self.inbox, self.calls = inbox, []

    def __call__(self, method, url, params=None, **kwargs):
        import base64
        from alfred_ai.services.public_http import PublicResponse
        self.calls.append((method, url, params))
        if url == "https://oauth2.googleapis.com/token":
            body = {"access_token": "synthetic-access"}
        elif url.endswith("/messages"):
            body = {"messages": [{"id": str(i)} for i in reversed(range(len(self.inbox)))]}  # newest first
        else:
            sender, subject, text = self.inbox[int(url.rsplit("/", 1)[1])]
            body = {"internalDate": "1794290400000", "payload": {
                "mimeType": "multipart/alternative", "headers": [{"name": "From", "value": sender}, {"name": "Subject", "value": subject}],
                "parts": [{"mimeType": "text/html", "body": {"data": ""}},
                          {"mimeType": "text/plain", "body": {"data": base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")}}]}}
        return PublicResponse(json.dumps(body).encode(), "application/json")


class ReplyWatchTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("synthetic-reply-owner", password="Test12345!")
        self.client.force_login(self.owner)
        self.pay = CareerJobAnalysis.objects.create(user=self.owner, job_url="https://jobs.example.test/1", job_title="Backend Engineer",
                                                    company="SyntheticPay Technologies", extracted_text="x",
                                                    extracted_payload={"application": {"stage": "applied", "history": [{"stage": "applied", "on": "2026-11-01"}]}})
        self.done = CareerJobAnalysis.objects.create(user=self.owner, job_url="https://jobs.example.test/2", job_title="Data Engineer",
                                                     company="Closed Corp", extracted_text="x",
                                                     extracted_payload={"application": {"stage": "rejected", "history": [{"stage": "rejected", "on": "2026-11-02"}]}})
        self.gmail = FakeGmail([
            ("Priya <priya@syntheticpay.com>", "Next steps", "We would like to schedule an interview. Share your availability."),
            ("jobs@closedcorp.io", "Closed Corp update", "We regret to inform you the position has been filled."),
            ("alerts@jobboard.test", "SyntheticPay jobs you may like", "Recommended jobs. Unsubscribe."),
            ("friend@example.test", "Dinner", "See you at 8."),
        ])

    def test_without_mail_setup_it_says_so_and_reads_nothing(self):
        from tests.test_career_send import connected
        self.assertFalse(self.client.get(URL).json()["replies_ready"])
        with patch("apps.career.services.career_mail.public_http.request", self.gmail):
            self.assertEqual(self.client.post(URL, {"operation": "replies"}, content_type="application/json").status_code, 400)
            connected(self, self.owner)
            from apps.career.services import career_mail
            career_mail._store(self.owner, {**career_mail._load(self.owner), "read": False})  # sending allowed, reading not ticked
            self.assertFalse(self.client.get(URL).json()["replies_ready"])
            self.assertEqual(self.client.post(URL, {"operation": "replies"}, content_type="application/json").status_code, 400)
        self.assertEqual(self.gmail.calls, [])

    def test_replies_are_sorted_read_only_and_never_change_a_stage_by_themselves(self):
        from tests.test_career_send import connected
        connected(self, self.owner)
        with patch("apps.career.services.career_mail.public_http.request", self.gmail):
            self.assertTrue(self.client.get(URL).json()["replies_ready"])
            replies = self.client.post(URL, {"operation": "replies"}, content_type="application/json").json()["result"]["replies"]
        self.assertEqual([(r["company"], r["category"], r["suggested_stage"]) for r in replies],
                         [("Closed Corp", "Rejected", None), ("SyntheticPay Technologies", "Interview", "interview")])  # noise and personal mail skipped
        self.assertEqual(replies[1]["because"], "interview")
        reads = self.gmail.calls[1:]
        self.assertEqual(reads[0][2], {"q": "in:inbox newer_than:30d", "maxResults": 200})
        self.assertEqual({method for method, *_ in reads}, {"GET"})  # read-only: nothing is marked read, moved or sent
        self.pay.refresh_from_db()
        self.assertEqual(self.pay.extracted_payload["application"]["stage"], "applied")  # unchanged until the owner applies
        self.assertNotIn("Share your availability", json.dumps(replies))  # the mail body is not passed on
        response = self.client.post(f"/api/career/job-analyses/{self.pay.pk}/application/", {"stage": "interview", "on": "2026-11-10"},
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_new_recruiter_email_with_a_jd_file_is_listed_and_analysed_only_on_request(self):
        import base64
        from alfred_ai.services.public_http import PublicResponse
        from tests.test_career_send import connected
        jd = b"Senior Python Developer at NovaSynth Labs. Required: Python, Django, SQL. 5+ years. Bengaluru."
        self.gmail.inbox.append(("Asha <asha@talentfirm.example>", "Senior Python Developer opening at NovaSynth",
                                 "Hi, I am recruiting for a Senior Python Developer role. JD attached."))
        lead = str(len(self.gmail.inbox) - 1)
        plain = self.gmail

        def gmail(method, url, params=None, **kwargs):
            if url.endswith(f"/messages/{lead}/attachments/att-1"):
                plain.calls.append((method, url, params))
                return PublicResponse(json.dumps({"data": base64.urlsafe_b64encode(jd).decode()}).encode(), "application/json")
            response = plain(method, url, params, **kwargs)
            if url.endswith(f"/messages/{lead}"):
                body = response.json()
                body["payload"]["parts"].append({"filename": "jd.txt", "mimeType": "text/plain", "body": {"attachmentId": "att-1", "size": len(jd)}})
                return PublicResponse(json.dumps(body).encode(), "application/json")
            return response

        connected(self, self.owner)
        with patch("apps.career.services.career_mail.public_http.request", gmail):
            result = self.client.post(URL, {"operation": "replies"}, content_type="application/json").json()["result"]
            self.assertEqual([(m["mail_id"], m["attachment"], m["because"]) for m in result["leads"]], [(lead, True, "opening")])
            self.assertEqual(CareerJobAnalysis.objects.filter(user=self.owner).count(), 2)  # listing saves nothing
            for bad in ({"mail_id": "../1"}, {"mail_id": lead, "message_text": "also this"}):
                self.assertEqual(self.client.post("/api/career/recruiter-match/", bad, content_type="application/json").status_code, 400)
            with patch("apps.career.views.verified_intelligence.macro_context", return_value={"payload": {}, "evidence": []}), \
                    patch("apps.career.views.job_intelligence.market_outlook", return_value={"risk_score": 30, "evidence": [], "insights": []}), \
                    patch("apps.career.views.job_intelligence.suggest_openings", return_value={"openings": [], "evidence": {}}):
                response = self.client.post("/api/career/recruiter-match/", {"mail_id": lead}, content_type="application/json")
        self.assertIn(response.status_code, (200, 201), response.content[:300])
        saved = CareerJobAnalysis.objects.filter(user=self.owner).latest("id")
        self.assertEqual(saved.source_document_name, "jd.txt")
        self.assertIn("Django", saved.extracted_text)
        self.assertIn("recruiting for a Senior Python Developer", saved.extracted_text)
        self.assertEqual({method for method, url, _ in self.gmail.calls if "gmail.googleapis.com" in url}, {"GET"})  # the mailbox is only read


def _xlsx(path, rows):
    """A minimal xlsx written by hand: shared strings for text, a bare number for the date serial."""
    import zipfile

    strings, sheet = [], []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, value in enumerate(row):
            ref = f"{chr(65 + c)}{r}"
            if isinstance(value, int):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                strings.append(value)
                cells.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
        sheet.append(f'<row r="{r}">{"".join(cells)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(path, "w") as book:
        book.writestr("xl/sharedStrings.xml", f'<sst {ns}>{"".join(f"<si><t>{s}</t></si>" for s in strings)}</sst>')
        book.writestr("xl/worksheets/sheet1.xml", f'<worksheet {ns}><sheetData>{"".join(sheet)}</sheetData></worksheet>')


class H1bSponsorTests(TestCase):
    def setUp(self):
        import tempfile

        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        patcher = patch.dict("os.environ", {"ALFRED_DATA_DIR": self.folder.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = get_user_model().objects.create_user("sponsor-owner", password="pw-12345678")
        self.client.force_login(self.user)

    def test_owner_imported_lca_file_gives_counted_history_never_a_promise(self):
        from pathlib import Path

        from apps.career.services import h1b_sponsor

        self.assertEqual(self.client.post(URL, {"operation": "sponsor_import"}, content_type="application/json").status_code, 400)
        imports = Path(self.folder.name) / "imports"
        imports.mkdir()
        header = ["CASE_STATUS", "RECEIVED_DATE", "VISA_CLASS", "EMPLOYER_NAME", "SECONDARY_ENTITY"]
        rows = [header] + [["Certified", 46000, "H-1B", "Acme Analytics, Inc.", "N"]] * 6 + \
            [["Denied", 46001, "H-1B", "Acme Analytics Inc", "N"], ["Certified", 46000, "E-3 Australian", "Acme Analytics", "N"]] + \
            [["Certified", 46000, "H-1B", "Body Shop Staffing LLC", "Y"]] * 3 + [["Certified", 40000, "H-1B", "Old Corp", "N"]]
        _xlsx(imports / "LCA_Disclosure_Data_FY2026_Q1.xlsx", rows)

        response = self.client.post(URL, {"operation": "sponsor_import"}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["result"]["employers"], 3)
        self.assertEqual(response.json()["sponsor"]["files"], [{"file": "LCA_Disclosure_Data_FY2026_Q1.xlsx", "h1b_rows": 11}])

        with patch.object(h1b_sponsor.timezone, "localdate", return_value=__import__("datetime").date(2026, 1, 1)):
            acme = self.client.post(URL, {"operation": "sponsor_check", "company": "ACME analytics"}, content_type="application/json").json()["result"]
            staffing = h1b_sponsor.check("Body Shop Staffing")
            old = h1b_sponsor.check("Old Corp")
            none = h1b_sponsor.check("Nobody Ltd")
        match = acme["matches"][0]
        self.assertEqual((match["filings"], match["certified"], match["tier"], match["latest"]), (7, 6, "active", "2025-12-10"))
        self.assertIn("not a promise", acme["basis"])
        self.assertEqual(staffing["matches"][0]["tier"], "staffing")
        self.assertEqual(old["matches"][0]["tier"], "weak")
        self.assertEqual(none["matches"], [])
        self.assertIn("not proof", none["basis"])

    def test_a_file_that_is_not_an_lca_export_is_refused(self):
        from pathlib import Path

        imports = Path(self.folder.name) / "imports"
        imports.mkdir()
        (imports / "LCA_notes.csv").write_text("name,city\nAcme,Austin\n", encoding="utf-8")
        response = self.client.post(URL, {"operation": "sponsor_import"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("not an LCA disclosure file", response.json()["detail"])
