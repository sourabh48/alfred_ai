"""WEALTH2-001: look-through of owner-uploaded fund portfolio files; synthetic files only, nothing stored."""
import io
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.sax.saxutils import escape

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from apps.investments.models import Investment, InvestmentImportDocument
from apps.investments.services.fund_look_through import LookThroughError, parse_portfolio

TODAY = date(2026, 11, 12)
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def xlsx(rows, shared=("Synthetic Alpha Flexi Cap Fund",), doctype=False):
    """A minimal workbook: text cells inline (or shared when listed in `shared`), numbers as values."""
    strings = list(shared)
    def cell(ref, value):
        if isinstance(value, (int, float, Decimal)):
            return f'<c r="{ref}"><v>{value}</v></c>'
        if value in strings:
            return f'<c r="{ref}" t="s"><v>{strings.index(value)}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
    body = "".join(f'<row r="{r}">' + "".join(cell(f"{chr(65 + c)}{r}", v) for c, v in enumerate(row) if v is not None) + "</row>"
                   for r, row in enumerate(rows, 1))
    head = '<?xml version="1.0"?>' + ('<!DOCTYPE x [<!ENTITY a "a">]>' if doctype else "")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{MAIN}" xmlns:r="{RELS}"><sheets><sheet name="Portfolio" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                         '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        archive.writestr("xl/sharedStrings.xml", f'<sst xmlns="{MAIN}">' + "".join(f"<si><t>{escape(s)}</t></si>" for s in strings) + "</sst>")
        archive.writestr("xl/worksheets/sheet1.xml", f'{head}<worksheet xmlns="{MAIN}"><sheetData>{body}</sheetData></worksheet>')
    return buffer.getvalue()


ALPHA = [
    ["Synthetic Alpha Flexi Cap Fund"],
    ["Portfolio as on 31-Oct-2026"],
    [],
    ["Name of the Instrument", "ISIN", "Industry / Rating", "Quantity", "Market Value (Rs. in Lakhs)", "% to Net Assets"],
    ["Equity & Equity related"],
    ["Synthetic Bank Ltd", "INE000A01011", "Banks", 1000, 812.5, 0.4],
    ["Synthetic Software Ltd", "INE000B01012", "IT - Software", 500, 300.1, 0.3],
    ["Synthetic US Chips Inc", "US0000000016", "Semiconductors", 10, 100.0, 0.2],
    ["Sub Total", None, None, None, 1212.6, 0.9],
    ["TREPS", None, None, None, 80.0, 0.12],
    ["Net Receivables / (Payables)", None, None, None, -20.0, -0.02],
    ["Grand Total", None, None, None, 1272.6, 1.0],
]
BETA_CSV = (
    "Synthetic Beta Large Cap Fund\nMonthly portfolio as on August 31, 2026\n"
    "Company,ISIN,Sector,% to NAV\n"
    "Synthetic Bank Ltd,INE000A01011,Banks,25.00%\n"
    "Synthetic Power Ltd,INE000C01013,Power,50.00%\n"
    "Synthetic Gold ETF units,INF000D01014,Fund units,20.00%\n"
    "Cash & equivalents,,,3.00%\n"
    "Total,,,98.00%\n"
).encode()


class FundPortfolioParserTests(TestCase):
    def test_xlsx_fraction_weights_skip_totals_and_keep_cash_opaque(self):
        parsed = parse_portfolio(xlsx(ALPHA), "alpha.xlsx")
        self.assertEqual((parsed["scheme"], parsed["as_of"]), ("Synthetic Alpha Flexi Cap Fund", date(2026, 10, 31)))
        weights = {item["isin"]: item["weight_pct"] for item in parsed["securities"]}
        self.assertEqual(weights, {"INE000A01011": Decimal("40.0"), "INE000B01012": Decimal("30.0"), "US0000000016": Decimal("20.0")})
        self.assertEqual([(item["name"], item["weight_pct"]) for item in parsed["opaque"]],
                         [("TREPS", Decimal("12.00")), ("Net Receivables / (Payables)", Decimal("-2.00"))])
        self.assertEqual(parsed["total_pct"], Decimal("100.00"))
        self.assertEqual(parsed["securities"][2]["country"], "US")

    def test_csv_percent_text_and_other_fund_units_are_opaque(self):
        parsed = parse_portfolio(BETA_CSV, "beta.csv")
        self.assertEqual(parsed["as_of"], date(2026, 8, 31))
        self.assertEqual(len(parsed["securities"]), 2)
        self.assertEqual([item["reason"] for item in parsed["opaque"]],
                         ["Another fund's units; its holdings are not in this file", "No security ISIN"])
        self.assertEqual(parsed["total_pct"], Decimal("98.00"))

    def test_unsupported_malformed_and_unsafe_files_are_refused(self):
        with self.assertRaises(LookThroughError):
            parse_portfolio(b"binary", "portfolio.xls")
        with self.assertRaises(LookThroughError):
            parse_portfolio(b"Name,Amount\nX,5\n", "no-table.csv")
        from alfred_ai.services.upload_limits import UploadFormatError
        for raw in (b"not a zip", xlsx(ALPHA, doctype=True)):
            with self.subTest(raw=raw[:8]), self.assertRaises(UploadFormatError):
                parse_portfolio(raw, "bad.xlsx")


class FundLookThroughApiTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-look-through-synthetic-")))
        self.media = root / "media"
        self.enterContext(override_settings(MEDIA_ROOT=self.media, ALFRED_ABUSE_THROTTLE_DIR=str(root / "limits")))
        self.enterContext(patch("apps.investments.look_through_views.timezone.localdate", return_value=TODAY))
        self.owner = get_user_model().objects.create_user(username="synthetic-look-through-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-look-through-other")
        self.alpha = Investment.objects.create(user=self.owner, asset_type="mutual_fund", asset_name="Alpha fund", current_value="100000.00", currency="INR")
        self.beta = Investment.objects.create(user=self.owner, asset_type="mutual_fund", asset_name="Beta fund", current_value="50000.00", currency="INR")
        self.client.force_login(self.owner)

    def post(self, pairs, client=None):
        files = [SimpleUploadedFile(name, raw) for _, raw, name in pairs]
        return (client or self.client).post("/api/investments/look-through/analyze/",
                                            {"file": files, "investment": [str(identity) for identity, _, _ in pairs]})

    def pairs(self):
        return [(self.alpha.pk, xlsx(ALPHA), "alpha.xlsx"), (self.beta.pk, BETA_CSV, "beta.csv")]

    def test_exposure_overlap_and_opaque_share_use_recorded_values_without_storing_anything(self):
        before = (Investment.objects.count(), InvestmentImportDocument.objects.count())
        response = self.post(self.pairs())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        data = response.json()
        self.assertEqual((data["currency"], data["total_value"]), ("INR", "150000.00"))
        bank = next(item for item in data["companies"] if item["isin"] == "INE000A01011")
        # 40% of 100,000 + 25% of 50,000
        self.assertEqual((bank["amount"], bank["share_pct"], len(bank["funds"])), ("52500.00", "35.00", 2))
        self.assertEqual(data["overlaps"], [{"funds": [self.alpha.pk, self.beta.pk], "common_securities": 1, "overlap_pct": "25.00"}])
        self.assertEqual({item["name"]: item["amount"] for item in data["countries"]}, {"IN": "107500.00", "US": "20000.00"})
        # Alpha 10% cash/receivables; Beta 20% fund units + 3% cash + 2% the file does not account for.
        self.assertEqual(data["opaque"], {"amount": "22500.00", "share_pct": "15.00"})
        beta = data["funds"][1]
        self.assertEqual((beta["unaccounted_pct"], beta["opaque_pct"]), ("2.00", "25.00"))
        self.assertTrue(any("31 Aug 2026" in warning for warning in beta["warnings"]))
        self.assertEqual(data["funds"][0]["warnings"], [])
        self.assertIn("Not available", data["currency_exposure"])
        self.assertEqual((Investment.objects.count(), InvestmentImportDocument.objects.count()), before)
        self.assertFalse(self.media.exists() and any(self.media.rglob("*")))
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.current_value, Decimal("100000.00"))

    def test_owner_isolation_choices_and_currency_mixing_are_refused(self):
        theirs = Investment.objects.create(user=self.other, asset_type="mutual_fund", asset_name="Theirs", current_value="1.00", currency="INR")
        usd = Investment.objects.create(user=self.owner, asset_type="mutual_fund", asset_name="USD fund", current_value="10.00", currency="USD")
        cases = {
            "other owner": [(theirs.pk, BETA_CSV, "beta.csv")],
            "same fund twice": [(self.alpha.pk, BETA_CSV, "a.csv"), (self.alpha.pk, BETA_CSV, "b.csv")],
            "mixed currency": [(self.alpha.pk, BETA_CSV, "a.csv"), (usd.pk, BETA_CSV, "b.csv")],
            "xls": [(self.alpha.pk, b"binary", "old.xls")],
            "broken xlsx": [(self.alpha.pk, b"not a zip", "bad.xlsx")],
            "too many": [(self.alpha.pk, BETA_CSV, "x.csv")] * 6,
        }
        for name, pairs in cases.items():
            with self.subTest(name):
                response = self.post(pairs)
                self.assertIn(response.status_code, (400, 413) if name == "too many" else (400,), response.content)
                self.assertNotIn("Theirs", response.content.decode())
        mismatched = self.client.post("/api/investments/look-through/analyze/", {"file": [SimpleUploadedFile("a.csv", BETA_CSV)], "investment": []})
        self.assertEqual(mismatched.status_code, 400)

    def test_sign_in_and_csrf_are_required(self):
        anonymous = Client()
        self.assertIn(self.post(self.pairs(), anonymous).status_code, (401, 403))
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.owner)
        self.assertEqual(self.post(self.pairs(), guarded).status_code, 403)
