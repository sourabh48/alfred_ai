"""Loan currency boundaries must survive the supported ORM write paths."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import SimpleTestCase, TestCase

from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanPaymentHistory
from apps.loans.money import loan_money, loan_money_float


MONEY_FIELDS = (
    "principal", "emi", "remaining_balance", "home_purchase_price",
    "home_down_payment", "home_other_upfront_payments", "total_paid",
)


class LoanMoneyBoundaryTests(SimpleTestCase):
    def test_half_cents_round_away_from_zero_for_charges_and_credits(self):
        cases = (
            ("1.005", "1.01"), ("-1.005", "-1.01"),
            (Decimal("2.675"), "2.68"), (Decimal("-2.675"), "-2.68"),
            ("0.005", "0.01"), ("-0.005", "-0.01"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                amount = loan_money(value)
                self.assertEqual(amount, Decimal(expected))
                self.assertEqual(amount.as_tuple().exponent, -2)

    def test_decimal_text_and_legacy_float_artifacts_resolve_to_currency(self):
        cases = (
            ("1234.5600", "1234.56"),
            (0.1 + 0.2, "0.30"),
            (2.675, "2.68"),
            (10 - 9.9, "0.10"),
            (None, "0.00"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(loan_money(value), Decimal(expected))

    def test_supported_signed_limit_and_roundable_values_below_it(self):
        for value, expected in (
            ("999999999999.99", "999999999999.99"),
            ("-999999999999.99", "-999999999999.99"),
            ("999999999999.994", "999999999999.99"),
            ("-999999999999.994", "-999999999999.99"),
        ):
            with self.subTest(value=value):
                self.assertEqual(loan_money(value), Decimal(expected))

    def test_nonfinite_boolean_malformed_and_out_of_range_values_are_rejected(self):
        invalid_values = (
            float("nan"), float("inf"), float("-inf"),
            Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
            "NaN", "-Infinity", True, False, "", "not money", "1,000.00",
            "999999999999.995", "-999999999999.995",
            "1000000000000", "-1000000000000", "1e1000",
        )
        for value in invalid_values:
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    loan_money(value)

    def test_numeric_output_adapter_rounds_at_the_currency_boundary(self):
        for value, expected in (("2.675", 2.68), (0.1 + 0.2, 0.3), (None, 0.0)):
            with self.subTest(value=value):
                result = loan_money_float(value)
                self.assertIsInstance(result, float)
                self.assertEqual(result, expected)


class LoanMoneyORMTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="loan-money-boundaries")

    def loan_values(self, **changes):
        values = {
            "user": self.user, "lender": "Currency Test Lender", "loan_type": "home",
            "principal": "100000.00", "emi": "1000.00", "interest_rate": 8,
            "remaining_balance": "75000.00", "tenure_months": 120,
            "start_date": date(2026, 1, 1),
        }
        values.update(changes)
        return values

    def assert_stored_money(self, loan, expected):
        loan.refresh_from_db()
        for name, amount in expected.items():
            with self.subTest(field=name):
                actual = getattr(loan, name)
                if amount is None:
                    self.assertIsNone(actual)
                else:
                    self.assertIsInstance(actual, Decimal)
                    self.assertEqual(actual, Decimal(amount))
                    self.assertEqual(actual.as_tuple().exponent, -2)

    def test_create_persists_all_seven_fields_as_rounded_currency(self):
        loan = Loan.objects.create(**self.loan_values(
            principal="100000.005", emi=2.675, remaining_balance="75000.005",
            home_purchase_price="150000.005", home_down_payment="50000.005",
            home_other_upfront_payments="2500.005", total_paid=0.1 + 0.2,
        ))
        self.assert_stored_money(loan, {
            "principal": "100000.01", "emi": "2.68", "remaining_balance": "75000.01",
            "home_purchase_price": "150000.01", "home_down_payment": "50000.01",
            "home_other_upfront_payments": "2500.01", "total_paid": "0.30",
        })

    def test_bulk_create_normalizes_values_without_model_save(self):
        first, second = Loan.objects.bulk_create([
            Loan(**self.loan_values(
                principal="100.005", emi="1.005", remaining_balance=None,
                home_purchase_price="150.005", home_down_payment="50.005",
                home_other_upfront_payments="2.675", total_paid=0.1 + 0.2,
            )),
            Loan(**self.loan_values(
                principal="-100.005", emi="-1.005", remaining_balance="0",
                home_purchase_price="-150.005", home_down_payment="-50.005",
                home_other_upfront_payments="-2.675", total_paid="-0.005",
            )),
        ])
        self.assert_stored_money(first, {
            "principal": "100.01", "emi": "1.01", "remaining_balance": None,
            "home_purchase_price": "150.01", "home_down_payment": "50.01",
            "home_other_upfront_payments": "2.68", "total_paid": "0.30",
        })
        self.assert_stored_money(second, {
            "principal": "-100.01", "emi": "-1.01", "remaining_balance": "0.00",
            "home_purchase_price": "-150.01", "home_down_payment": "-50.01",
            "home_other_upfront_payments": "-2.68", "total_paid": "-0.01",
        })

    def test_partial_save_rounds_selected_fields_and_preserves_other_values(self):
        loan = Loan.objects.create(**self.loan_values())
        loan.emi = "1234.565"
        loan.total_paid = 0.1 + 0.2
        loan.home_down_payment = "99.995"
        loan.save(update_fields=["emi", "total_paid"])
        self.assert_stored_money(loan, {
            "emi": "1234.57", "total_paid": "0.30", "home_down_payment": "0.00",
            "principal": "100000.00", "remaining_balance": "75000.00",
        })

    def test_queryset_update_rounds_all_seven_fields(self):
        loan = Loan.objects.create(**self.loan_values())
        changed = Loan.objects.filter(pk=loan.pk).update(
            principal="-100.005", emi="2.675", remaining_balance=0.1 + 0.2,
            home_purchase_price="150.005", home_down_payment="50.005",
            home_other_upfront_payments="-0.005", total_paid="20.005",
        )
        self.assertEqual(changed, 1)
        self.assert_stored_money(loan, {
            "principal": "-100.01", "emi": "2.68", "remaining_balance": "0.30",
            "home_purchase_price": "150.01", "home_down_payment": "50.01",
            "home_other_upfront_payments": "-0.01", "total_paid": "20.01",
        })

    def test_null_balance_and_explicit_zero_survive_create_save_and_update(self):
        loan = Loan.objects.create(**self.loan_values(remaining_balance=None))
        self.assert_stored_money(loan, {"remaining_balance": None})
        loan.remaining_balance = 0
        loan.save(update_fields=["remaining_balance"])
        self.assert_stored_money(loan, {"remaining_balance": "0.00"})
        Loan.objects.filter(pk=loan.pk).update(remaining_balance=None)
        self.assert_stored_money(loan, {"remaining_balance": None})
        Loan.objects.filter(pk=loan.pk).update(remaining_balance="0.005")
        self.assert_stored_money(loan, {"remaining_balance": "0.01"})

    def test_signed_maximum_persists_exactly_in_every_money_field(self):
        for amount in ("999999999999.99", "-999999999999.99"):
            with self.subTest(amount=amount):
                loan = Loan.objects.create(**self.loan_values(**{name: amount for name in MONEY_FIELDS}))
                self.assert_stored_money(loan, {name: amount for name in MONEY_FIELDS})
                stored = Loan.objects.filter(pk=loan.pk).values_list(*MONEY_FIELDS).get()
                self.assertEqual(stored, (Decimal(amount),) * len(MONEY_FIELDS))

    def test_rejected_queryset_writes_preserve_prior_values(self):
        loan = Loan.objects.create(**self.loan_values())
        before = Loan.objects.filter(pk=loan.pk).values(*MONEY_FIELDS).get()
        for invalid in (float("nan"), float("inf"), True, "bad money", "999999999999.995"):
            with self.subTest(value=repr(invalid)):
                with self.assertRaises(ValidationError):
                    with transaction.atomic():
                        Loan.objects.filter(pk=loan.pk).update(principal="12.34", emi=invalid)
                self.assertEqual(Loan.objects.filter(pk=loan.pk).values(*MONEY_FIELDS).get(), before)

    def test_rejected_partial_save_preserves_existing_loan(self):
        loan = Loan.objects.create(**self.loan_values())
        loan.emi = Decimal("Infinity")
        loan.remaining_balance = "0"
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                loan.save(update_fields=["emi", "remaining_balance"])
        self.assert_stored_money(loan, {"emi": "1000.00", "remaining_balance": "75000.00"})

    def test_invalid_later_bulk_batch_rolls_back_the_whole_create(self):
        before = Loan.objects.count()
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                Loan.objects.bulk_create([
                    Loan(**self.loan_values(lender="Valid first batch")),
                    Loan(**self.loan_values(lender="Invalid second batch", total_paid=False)),
                ], batch_size=1)
        self.assertEqual(Loan.objects.count(), before)

    def test_home_properties_use_exact_cents_then_return_numeric_values(self):
        loan = Loan.objects.create(**self.loan_values(
            principal="0.10", remaining_balance="0.10", home_down_payment="0.20",
            home_other_upfront_payments="0.10",
        ))
        loan.refresh_from_db()
        for name, expected in (
            ("resolved_home_purchase_price", 0.3),
            ("resolved_home_down_payment", 0.2),
            ("resolved_home_upfront_cash_invested", 0.3),
            ("resolved_home_property_acquisition_cost", 0.4),
        ):
            with self.subTest(property=name):
                actual = getattr(loan, name)
                self.assertIsInstance(actual, float)
                self.assertEqual(actual, expected)
        loan.home_purchase_price = "0.30"
        loan.save(update_fields=["home_purchase_price"])
        loan.refresh_from_db()
        self.assertEqual(loan.resolved_home_down_payment, 0.2)
        self.assertEqual(loan.resolved_home_upfront_cash_invested, 0.3)

    def test_home_property_totals_can_exceed_the_individual_field_limit(self):
        loan = Loan.objects.create(**self.loan_values(
            principal="999999999999.99", home_down_payment="999999999999.99",
            home_purchase_price="0.00", home_other_upfront_payments="1.00",
        ))
        self.assert_stored_money(loan, {
            "principal": "999999999999.99", "home_down_payment": "999999999999.99",
            "home_purchase_price": "0.00", "home_other_upfront_payments": "1.00",
        })
        for name, expected in (
            ("resolved_home_purchase_price", 1999999999999.98),
            ("resolved_home_property_acquisition_cost", 2000000000000.98),
            ("resolved_home_upfront_cash_invested", 1000000000000.99),
        ):
            with self.subTest(property=name):
                actual = getattr(loan, name)
                self.assertIsInstance(actual, float)
                self.assertEqual(actual, expected)

    def test_completion_preserves_unknown_balance_and_numeric_zero_completion(self):
        loan = Loan.objects.create(**self.loan_values(principal="0.30", remaining_balance=None))
        loan.refresh_from_db()
        self.assertEqual(loan.completion_percentage, 0.0)
        loan.remaining_balance = "0.00"
        loan.save(update_fields=["remaining_balance"])
        loan.refresh_from_db()
        self.assertIsInstance(loan.completion_percentage, float)
        self.assertEqual(loan.completion_percentage, 100.0)
        loan.principal = "0.00"
        loan.save(update_fields=["principal"])
        loan.refresh_from_db()
        self.assertEqual(loan.completion_percentage, 100.0)

    def test_related_money_fields_reuse_the_cent_boundary_and_preserve_null(self):
        loan = Loan.objects.create(**self.loan_values())
        payment_fields = (
            "amount", "principal_component", "interest_component", "principal_paid",
            "interest_paid", "charges_paid", "penalties_paid", "tax_paid", "remaining_balance",
        )
        foreclosure_fields = (
            "outstanding_principal", "accrued_interest", "foreclosure_charges", "taxes_gst",
            "overdue_charges", "total_amount_payable", "matched_payment_total",
        )
        payment = LoanPaymentHistory.objects.create(
            loan=loan, payment_date=date(2026, 1, 2),
            **dict.fromkeys(payment_fields, "1.005"),
        )
        document = LoanClosureDocument.objects.create(
            loan=loan, file_name="boundary.pdf", closure_amount="1.005",
        )
        snapshot = LoanForeclosureSnapshot.objects.create(
            loan=loan, closure_document=document, **dict.fromkeys(foreclosure_fields, "1.005"),
        )
        for row, fields in (
            (payment, payment_fields), (document, ("closure_amount",)),
            (snapshot, foreclosure_fields),
        ):
            with self.subTest(model=type(row).__name__):
                row.refresh_from_db()
                for field in fields:
                    self.assertEqual(getattr(row, field), Decimal("1.01"), field)
                type(row).objects.filter(pk=row.pk).update(
                    **dict.fromkeys(fields, "-999999999999.99"),
                )
                row.refresh_from_db()
                self.assertEqual(
                    tuple(getattr(row, field) for field in fields),
                    (Decimal("-999999999999.99"),) * len(fields),
                )
                with self.assertRaises(ValidationError), transaction.atomic():
                    type(row).objects.filter(pk=row.pk).update(**{fields[0]: "Infinity"})
                row.refresh_from_db()
                self.assertEqual(getattr(row, fields[0]), Decimal("-999999999999.99"))
        LoanPaymentHistory.objects.filter(pk=payment.pk).update(remaining_balance=None)
        payment.refresh_from_db()
        self.assertIsNone(payment.remaining_balance)
        LoanPaymentHistory.objects.filter(pk=payment.pk).update(remaining_balance="0")
        payment.refresh_from_db()
        self.assertEqual(payment.remaining_balance, Decimal("0.00"))
