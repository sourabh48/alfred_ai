"""A data reset includes pre-migration money evidence, even for deleted loans."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.loans.models import Loan, LoanMoneySnapshot
from apps.users.services import clear_user_fed_data


class LoanMoneyRetentionTests(TestCase):
    def test_reset_removes_owned_orphan_snapshot_and_preserves_other_owner(self):
        user = get_user_model().objects.create_user(username="money-reset")
        other = get_user_model().objects.create_user(username="other-money-reset")
        snapshots = []
        for owner in (user, other):
            loan = Loan.objects.create(user=owner, principal=1000, emi=100,
                                       interest_rate=0, start_date=timezone.localdate())
            snapshots.append(LoanMoneySnapshot.objects.create(
                user=owner, loan=loan, original_loan_id=loan.pk,
                source_values={"principal": "1000.005"}, normalized_values={"principal": "1000.01"},
            ))
            if owner == user:
                loan.delete()
        snapshots[0].refresh_from_db()
        self.assertIsNone(snapshots[0].loan_id)
        summary = clear_user_fed_data(user)
        self.assertEqual(summary["loan_money_snapshots"], 1)
        self.assertFalse(LoanMoneySnapshot.objects.filter(user=user).exists())
        self.assertTrue(LoanMoneySnapshot.objects.filter(pk=snapshots[1].pk, user=other).exists())
        self.assertEqual(Loan.objects.filter(user=other).count(), 1)
