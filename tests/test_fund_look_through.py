"""WEALTH2-001: look-through of owner-uploaded fund portfolio files; synthetic files only."""
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
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase, override_settings

from apps.investments.models import FundPortfolioSnapshot, Investment, InvestmentImportDocument
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


def beta_csv(as_of="August 31, 2026"):
    return BETA_CSV.replace(b"August 31, 2026", as_of.encode())


class SavedFundPortfolioTests(FundLookThroughApiTests):
    def post(self, pairs, client=None, save=True):
        files = [SimpleUploadedFile(name, raw) for _, raw, name in pairs]
        data = {"file": files, "investment": [str(identity) for identity, _, _ in pairs]}
        return (client or self.client).post("/api/investments/look-through/analyze/", {**data, "save": "1"} if save else data)

    def saved(self, ids, client=None):
        return (client or self.client).post("/api/investments/look-through/saved/", {"investment": ids}, content_type="application/json")

    def test_save_keeps_only_parsed_rows_and_saved_look_through_matches_the_files(self):
        fresh = self.post(self.pairs(), save=False).json()
        self.assertFalse(FundPortfolioSnapshot.objects.exists())
        saved = self.post(self.pairs()).json()
        self.assertTrue(all(fund["saved_snapshot"] for fund in saved["funds"]))
        self.assertIn("not the file itself", saved["limits"][-1])
        self.post(self.pairs())  # the same files again are not saved twice
        self.assertEqual(FundPortfolioSnapshot.objects.filter(user=self.owner).count(), 2)
        alpha = FundPortfolioSnapshot.objects.get(investment=self.alpha)
        self.assertEqual((alpha.scheme, alpha.as_of, len(alpha.securities)), ("Synthetic Alpha Flexi Cap Fund", date(2026, 10, 31), 3))
        self.assertEqual(Decimal(alpha.securities[0]["weight_pct"]), Decimal("40"))
        self.assertFalse(self.media.exists() and any(self.media.rglob("*")))
        listing = self.client.get("/api/investments/look-through/saved/")
        self.assertIn("no-store", listing["Cache-Control"])
        self.assertEqual({row["holding"] for row in listing.json()}, {"Alpha fund", "Beta fund"})
        reused = self.saved([self.alpha.pk, self.beta.pk])
        self.assertEqual(reused.status_code, 200, reused.content)
        data = reused.json()
        for key in ("total_value", "companies", "sectors", "countries", "opaque", "overlaps"):
            self.assertEqual(data[key], fresh[key], key)
        self.assertEqual([fund["warnings"] for fund in data["funds"]], [fund["warnings"] for fund in fresh["funds"]])
        self.assertEqual(data["funds"][0]["source"]["saved_snapshot"], alpha.pk)
        self.alpha.refresh_from_db()
        self.assertEqual(self.alpha.current_value, Decimal("100000.00"))

    def test_the_latest_three_portfolios_per_holding_are_kept(self):
        for day in ("May 31, 2026", "June 30, 2026", "July 31, 2026", "August 31, 2026"):
            self.assertEqual(self.post([(self.beta.pk, beta_csv(day), "beta.csv")]).status_code, 200)
        kept = list(FundPortfolioSnapshot.objects.filter(investment=self.beta).values_list("as_of", flat=True))
        self.assertEqual(kept, [date(2026, 8, 31), date(2026, 7, 31), date(2026, 6, 30)])
        older = self.post([(self.beta.pk, beta_csv("April 30, 2026"), "beta.csv")]).json()["funds"][0]
        self.assertIsNone(older["saved_snapshot"])
        self.assertTrue(any("Not saved" in warning for warning in older["warnings"]))
        self.assertEqual(FundPortfolioSnapshot.objects.filter(investment=self.beta).count(), 3)
        self.assertEqual(self.saved([self.beta.pk]).json()["funds"][0]["as_of"], "2026-08-31")

    def test_saved_portfolios_stay_with_their_owner(self):
        self.post(self.pairs())
        mine = FundPortfolioSnapshot.objects.get(investment=self.alpha)
        other = Client()
        other.force_login(self.other)
        self.assertEqual(other.get("/api/investments/look-through/saved/").json(), [])
        self.assertEqual(self.saved([self.alpha.pk], other).status_code, 400)
        self.assertEqual(other.delete(f"/api/investments/look-through/saved/{mine.pk}/").status_code, 404)
        no_snapshot = Investment.objects.create(user=self.owner, asset_type="mutual_fund", asset_name="Gamma fund", current_value="1.00", currency="INR")
        for body in ({"investment": [no_snapshot.pk]}, {"investment": [str(self.alpha.pk)]}, {"investment": [True]}, {"investment": []}, [self.alpha.pk]):
            with self.subTest(body=body):
                response = self.client.post("/api/investments/look-through/saved/", body, content_type="application/json")
                self.assertEqual(response.status_code, 400, response.content)
        self.assertIn(Client().get("/api/investments/look-through/saved/").status_code, (401, 403))
        self.assertEqual(self.client.delete(f"/api/investments/look-through/saved/{mine.pk}/").status_code, 204)
        self.assertFalse(FundPortfolioSnapshot.objects.filter(pk=mine.pk).exists())
        self.assertTrue(Investment.objects.filter(pk=self.alpha.pk).exists())

    def test_data_reset_and_deleting_the_holding_remove_saved_portfolios(self):
        from apps.users.services import clear_user_fed_data
        self.post(self.pairs())
        self.beta.delete()
        self.assertEqual(list(FundPortfolioSnapshot.objects.values_list("investment_id", flat=True)), [self.alpha.pk])
        clear_user_fed_data(self.owner)
        self.assertFalse(FundPortfolioSnapshot.objects.exists())


class FundPortfolioSnapshotMigrationTests(TransactionTestCase):
    def test_forward_and_guarded_reverse_on_a_disposable_database(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before = [("investments", "0007_research_decision") if app == "investments" else (app, name) for app, name in leaves]
        target = [("investments", "0008_fund_portfolio_snapshot") if app == "investments" else (app, name) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-fund-snapshot-synthetic-") as directory:
            alias = "fund_snapshot_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(Path(directory) / "snapshots.sqlite3")
            connections[alias] = db
            try:
                MigrationExecutor(db).migrate(target)
                apps = MigrationExecutor(db).loader.project_state(target).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(username="synthetic-snapshot-owner")
                holding = apps.get_model("investments", "Investment").objects.using(alias).create(
                    user_id=owner.pk, asset_type="mutual_fund", asset_name="Synthetic fund")
                row = apps.get_model("investments", "FundPortfolioSnapshot").objects.using(alias).create(
                    user_id=owner.pk, investment_id=holding.pk, source_sha256="0" * 64)
                with self.assertRaisesMessage(RuntimeError, "Restore the verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before)
                self.assertIn("investments_fundportfoliosnapshot", db.introspection.table_names())
                apps.get_model("investments", "FundPortfolioSnapshot").objects.using(alias).filter(pk=row.pk).delete()
                MigrationExecutor(db).migrate(before)
                self.assertNotIn("investments_fundportfoliosnapshot", db.introspection.table_names())
                self.assertEqual(apps.get_model("investments", "Investment").objects.using(alias).count(), 1)
            finally:
                db.close()
