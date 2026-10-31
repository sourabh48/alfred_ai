"""Date boundaries for the Asia/Kolkata default. Every instant is frozen, so these pass at any hour on any machine."""
from datetime import date, datetime, timedelta, timezone as utc_timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.budgets.services.budget_intelligence import current_budget_plan
from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.multi_bank_aggregator import MultiBankAggregatorService
from apps.loans.models import Loan
from apps.loans.services.payment_review import _predates_verified_balance
from apps.ml_engine.services.tax_optimizer import TaxOptimizerService
from apps.mobility.planner_views import photo_matches
from apps.mobility.services.travel.reminders import schedule

INDIA = ZoneInfo("Asia/Kolkata")
CHICAGO = "America/Chicago"


def utc(*parts):
    return datetime(*parts, tzinfo=utc_timezone.utc)


def frozen(instant):
    return patch("django.utils.timezone.now", return_value=instant)


class DefaultZoneTests(SimpleTestCase):
    def test_default_is_india_and_now_stays_utc(self):
        self.assertEqual(settings.TIME_ZONE, "Asia/Kolkata")
        self.assertTrue(settings.USE_TZ)
        self.assertEqual(timezone.get_default_timezone_name(), "Asia/Kolkata")
        self.assertEqual(timezone.now().utcoffset(), timedelta(0))


class DateBoundaryTests(SimpleTestCase):
    # Label, instant, India date, Chicago date.
    BOUNDARIES = (
        ("just before UTC midnight", utc(2026, 10, 30, 23, 59, 59), date(2026, 10, 31), date(2026, 10, 30)),
        ("UTC midnight", utc(2026, 10, 31), date(2026, 10, 31), date(2026, 10, 30)),
        ("just before IST midnight", utc(2026, 10, 31, 18, 29, 59), date(2026, 10, 31), date(2026, 10, 31)),
        ("IST midnight and month rollover", utc(2026, 10, 31, 18, 30), date(2026, 11, 1), date(2026, 10, 31)),
        ("IST midnight and year rollover", utc(2026, 12, 31, 18, 30), date(2027, 1, 1), date(2026, 12, 31)),
        ("IST midnight and financial year rollover", utc(2027, 3, 31, 18, 30), date(2027, 4, 1), date(2027, 3, 31)),
    )

    def test_localdate_follows_india_at_every_boundary(self):
        for label, instant, india, chicago in self.BOUNDARIES:
            with self.subTest(label), frozen(instant):
                self.assertEqual(timezone.localdate(), india)
                # The defect: the same instant under the former default.
                with override_settings(TIME_ZONE=CHICAGO):
                    self.assertEqual(timezone.localdate(), chicago)

    def lag_hours(self, day):
        midnight = datetime(day.year, day.month, day.day, tzinfo=INDIA).astimezone(utc_timezone.utc)
        steps = 0
        for step in range(48):
            with frozen(midnight + timedelta(minutes=30 * step)):
                steps += timezone.localdate() != day
        return steps / 2

    def test_former_chicago_lag_changes_with_dst_and_india_never_lags(self):
        expected = {
            date(2026, 10, 15): 10.5,  # Daylight time.
            date(2026, 11, 1): 10.5,  # Chicago's day started before its clocks went back.
            date(2026, 11, 2): 11.5,  # First full standard-time day.
            date(2026, 12, 15): 11.5,
            date(2027, 3, 14): 11.5,  # Chicago's day started before its clocks went forward.
            date(2027, 3, 15): 10.5,
        }
        for day, hours in expected.items():
            with self.subTest(day=day):
                self.assertEqual(self.lag_hours(day), 0)
                with override_settings(TIME_ZONE=CHICAGO):
                    self.assertEqual(self.lag_hours(day), hours)


class FinancialConsumerBoundaryTests(SimpleTestCase):
    FIRST_MINUTE_OF_NOVEMBER = utc(2026, 10, 31, 18, 30)
    LAST_SECOND_OF_OCTOBER = utc(2026, 10, 31, 18, 29, 59)

    def test_new_expense_defaults_to_the_india_date(self):
        with frozen(self.FIRST_MINUTE_OF_NOVEMBER):
            self.assertEqual(Expense().transaction_date, date(2026, 11, 1))

    def test_active_budget_plan_rolls_over_at_ist_midnight(self):
        october, november = SimpleNamespace(month="Oct 2026"), SimpleNamespace(month="2026-11")
        with frozen(self.LAST_SECOND_OF_OCTOBER):
            self.assertIs(current_budget_plan(None, budgets=[november, october]), october)
        with frozen(self.FIRST_MINUTE_OF_NOVEMBER):
            self.assertIs(current_budget_plan(None, budgets=[november, october]), november)

    def test_loan_months_remaining_counts_from_the_india_month(self):
        loan = Loan(start_date=date(2026, 11, 1), tenure_months=1)
        with frozen(self.LAST_SECOND_OF_OCTOBER):
            self.assertEqual(loan.months_remaining, 2)
        with frozen(self.FIRST_MINUTE_OF_NOVEMBER):
            self.assertEqual(loan.months_remaining, 1)

    def test_tax_financial_year_rolls_over_at_ist_midnight(self):
        with frozen(utc(2027, 3, 31, 18, 29, 59)):
            self.assertEqual(TaxOptimizerService()._current_financial_year_bounds(), (date(2026, 4, 1), date(2027, 3, 31)))
        with frozen(utc(2027, 3, 31, 18, 30)):
            self.assertEqual(TaxOptimizerService()._current_financial_year_bounds(), (date(2027, 4, 1), date(2028, 3, 31)))

    def test_verified_balance_cutoff_uses_the_india_date_of_the_stored_instant(self):
        verified_at = utc(2026, 10, 31, 19, 0)  # 00:30 IST on 1 November; still 31 October in Chicago.
        loan = SimpleNamespace(verified_at=verified_at)

        def predates(payment_date):
            return _predates_verified_balance(SimpleNamespace(
                loan=loan, created_at=verified_at + timedelta(hours=1), payment_date=payment_date))

        self.assertTrue(predates(date(2026, 11, 1)))
        self.assertFalse(predates(date(2026, 11, 2)))
        # The stored instant is unchanged; only its date under the former default differs.
        with override_settings(TIME_ZONE=CHICAGO):
            self.assertFalse(predates(date(2026, 11, 1)))


class StoredValueTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="time_zone_boundary", password="Pass12345!")
        self.account = BankAccount.objects.create(user=self.user, account_number="000000001")

    def expense(self, day, amount):
        return Expense.objects.create(user=self.user, bank_account=self.account, amount=Decimal(amount), transaction_date=day)

    def test_month_window_rolls_over_at_ist_midnight_without_moving_dates(self):
        self.expense(date(2026, 10, 31), "100.00")
        self.expense(date(2026, 11, 1), "7.00")

        def monthly_spending():
            return MultiBankAggregatorService().get_consolidated_view(self.user)["accounts"][0]["monthly_spending"]

        with frozen(utc(2026, 10, 31, 18, 29, 59)):
            self.assertEqual(monthly_spending(), 107.0)
        with frozen(utc(2026, 10, 31, 18, 30)):
            self.assertEqual(monthly_spending(), 7.0)

    def test_stored_transaction_date_is_never_reinterpreted_and_timestamps_stay_utc(self):
        with frozen(utc(2026, 10, 31, 19, 0)):
            row = self.expense(date(2026, 10, 31), "1.00")

        def stored(column):
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT {column} FROM {Expense._meta.db_table} WHERE id = %s", [row.pk])
                return str(cursor.fetchone()[0])

        for zone in ("Asia/Kolkata", CHICAGO, "UTC"):
            with self.subTest(zone=zone), override_settings(TIME_ZONE=zone):
                self.assertEqual(Expense.objects.get(pk=row.pk).transaction_date, date(2026, 10, 31))
                self.assertEqual(stored("transaction_date"), "2026-10-31")
                self.assertTrue(stored("timestamp").startswith("2026-10-31 19:00:00"))


class ExplicitZoneTests(SimpleTestCase):
    def test_reminder_uses_its_own_zone_whatever_the_application_default(self):
        cases = (
            (("Asia/Kolkata", "2026-11-01T00:00"), "2026-10-31T18:30:00+00:00"),  # Across UTC midnight's date.
            ((CHICAGO, "2026-07-01T10:00"), "2026-07-01T15:00:00+00:00"),  # Daylight time.
            ((CHICAGO, "2026-12-01T10:00"), "2026-12-01T16:00:00+00:00"),  # Standard time.
            ((CHICAGO, "2026-11-01T01:30", 0), "2026-11-01T06:30:00+00:00"),  # Repeated hour, first.
            ((CHICAGO, "2026-11-01T01:30", 1), "2026-11-01T07:30:00+00:00"),  # Repeated hour, second.
        )
        for zone in ("Asia/Kolkata", CHICAGO):
            for arguments, instant in cases:
                with self.subTest(default=zone, arguments=arguments), override_settings(TIME_ZONE=zone):
                    self.assertEqual(schedule(*arguments)[0], instant)

    def test_reminder_refuses_chicago_clock_change_times(self):
        for local_time in ("2026-11-01T01:30", "2027-03-14T02:30"):  # Repeated without a choice; skipped.
            with self.subTest(local_time=local_time), self.assertRaises(ValidationError):
                schedule(CHICAGO, local_time)

    def test_photo_taken_late_on_the_last_trip_day_stays_on_that_day(self):
        plan = SimpleNamespace(id=1, start_date=date(2026, 10, 30), end_date=date(2026, 10, 31), destination="Mysuru")

        def photo(naive):
            return SimpleNamespace(taken_at=timezone.make_aware(naive), ignored_plan_ids=[], location_name="Mysuru")

        self.assertTrue(photo_matches(photo(datetime(2026, 10, 31, 23, 30)), plan))
        self.assertFalse(photo_matches(photo(datetime(2026, 11, 1, 0, 30)), plan))
