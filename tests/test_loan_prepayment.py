"""Wealth 2.0 loan prepayment what-if: Decimal amortization, prepay versus invest, liquidity, read-only API."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.loans.models import Loan
from apps.loans.services.prepayment import level_emi, liquidity_after, schedule, simulate

D = Decimal


class AmortizationTests(SimpleTestCase):
    def test_known_answers(self):
        # 1,00,000 at 12% a year over 12 months: the textbook EMI is 8,884.88 and interest about 6,618.5.
        emi = level_emi(D("100000"), 12, D("0.01"))
        self.assertEqual(emi, D("8884.88"))
        rows = schedule(D("100000.00"), emi, D("0.01"))
        self.assertEqual(len(rows), 12)
        self.assertTrue(D("6618.40") <= sum(row[1] for row in rows) <= D("6618.70"))
        self.assertEqual(len(schedule(D("1000.00"), D("300.00"), D("0"))), 4)  # zero rate: 300, 300, 300, 100
        self.assertIsNone(schedule(D("100000.00"), D("1000.00"), D("0.01")))  # EMI equals the interest

    def test_prepayment_modes_and_closing(self):
        base = dict(balance="100000", emi="8884.88", annual_rate=12)
        tenure = simulate(**base, amount="50000")
        self.assertEqual(tenure["baseline"]["months"], 12)
        self.assertLess(tenure["after"]["months"], 12)
        self.assertGreater(tenure["interest_saved"], 0)
        lower = simulate(**base, amount="50000", mode="reduce_emi")
        self.assertEqual((lower["after"]["months"], lower["after"]["emi"]), (12, D("4442.44")))
        self.assertGreater(tenure["interest_saved"], lower["interest_saved"])  # paying off sooner saves more interest
        closed = simulate(**base, amount="999999")
        self.assertEqual((closed["mode"], closed["prepayment"], closed["after"]["months"]), ("closes_loan", D("100000.00"), 0))
        self.assertEqual(closed["interest_saved"], closed["baseline"]["total_interest"])
        for bad in ({"amount": "0"}, {"amount": "10", "mode": "skip"}, {"amount": "10", "emi": "500"}):
            with self.subTest(bad), self.assertRaises(ValueError):
                simulate(**{**base, **bad})

    def test_prepay_versus_invest_follows_both_paths_to_the_original_end(self):
        base = dict(balance="100000", emi="8884.88", annual_rate=12, amount="50000")
        nothing = simulate(**base, expected_return=0)["versus_investing"]
        self.assertEqual((nothing["better"], nothing["invest_path_value"]), ("prepay", D("50000.00")))
        self.assertEqual(simulate(**base, expected_return=30)["versus_investing"]["better"], "invest")
        for mode in ("reduce_tenure", "reduce_emi"):
            # Earning exactly the loan rate makes the two paths equal apart from paisa rounding.
            same = simulate(**base, mode=mode, expected_return=12)["versus_investing"]
            self.assertLess(same["difference"], D("50"), (mode, same))

    def test_liquidity_runway(self):
        baseline = {"liquid_cash": 300000, "essential_monthly_outflow": 20000}
        self.assertEqual(liquidity_after(baseline, D("50000"))["status"], "kept")
        thin = liquidity_after(baseline, D("200000"))
        self.assertEqual((thin["status"], thin["runway_months_after"]), ("thin", D("5.0")))
        self.assertEqual(liquidity_after(baseline, D("400000"))["status"], "short")
        self.assertEqual(liquidity_after({"liquid_cash": 5}, D("1"))["status"], "unknown")


class PrepaymentApiTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-prepay-owner")
        self.client.force_login(self.owner)
        self.loan = Loan.objects.create(user=self.owner, principal=D("100000.00"), remaining_balance=D("100000.00"), emi=D("8884.88"),
                                        interest_rate=12, tenure_months=12, start_date=timezone.localdate())

    def ask(self, loan, **params):
        return self.client.get(f"/api/loans/{loan.pk}/prepayment/", params)

    def test_what_if_is_read_only_and_explains_its_assumptions(self):
        before = Loan.objects.values().get(pk=self.loan.pk)
        data = self.ask(self.loan, amount="50000", expected_return="8").json()
        self.assertEqual((data["baseline"]["months"], data["currency"], data["liquidity"]["status"]), (12, None, "short"))  # its own EMI is essential spending; no bank balance recorded
        self.assertGreater(data["interest_saved"], 0)
        self.assertIn(data["versus_investing"]["better"], {"prepay", "invest", "equal"})
        self.assertEqual(len(data["assumptions"]), 3)
        self.assertEqual(Loan.objects.values().get(pk=self.loan.pk), before)

    def test_refusals(self):
        for params in ({"amount": ""}, {"amount": "abc"}, {"amount": "-5"}, {"amount": "10", "expected_return": "45"},
                       {"amount": "10", "expected_return": "NaN"}, {"amount": "10", "mode": "x"}):
            with self.subTest(params):
                self.assertEqual(self.ask(self.loan, **params).status_code, 400)
        unknown = Loan.objects.create(user=self.owner, principal=D("10.00"), emi=D("1.00"), interest_rate=1, start_date=timezone.localdate())
        self.assertIn("never guessed", self.ask(unknown, amount="1").json()["detail"])
        closed = Loan.objects.create(user=self.owner, principal=D("10.00"), remaining_balance=D("0.00"), emi=D("1.00"), interest_rate=1,
                                     start_date=timezone.localdate(), status="closed", is_active=False)
        self.assertEqual(self.ask(closed, amount="1").status_code, 400)
        other = get_user_model().objects.create_user(username="synthetic-prepay-other")
        theirs = Loan.objects.create(user=other, principal=D("10.00"), remaining_balance=D("10.00"), emi=D("1.00"), interest_rate=1,
                                     start_date=timezone.localdate())
        self.assertEqual(self.ask(theirs, amount="1").status_code, 404)
