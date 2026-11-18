"""'Can I afford X?' gets a fixed answer from the canonical baseline, never model arithmetic."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from alfred_ai.services.currency import rupee_text
from apps.expenses.models import BankAccount
from apps.ml_engine.services.affordability import asked_amount
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer


class AskedAmountTests(SimpleTestCase):
    def test_reads_the_price_in_plain_indian_wording(self):
        self.assertEqual(asked_amount("I am not good with money. Can I afford a 30000 rupee phone this month?"), Decimal("30000"))
        self.assertEqual(asked_amount("can i afford a 1.5 lakh bike"), Decimal("150000.0"))
        self.assertEqual(asked_amount("Should I buy a 45k laptop?"), Decimal("45000"))
        self.assertEqual(asked_amount("Can I afford ₹2,50,000 for a wedding?"), Decimal("250000"))
        for other in ("What is my balance?", "Can I afford it?", "What did I spend 30000 on?"):
            self.assertIsNone(asked_amount(other), other)

    def test_rupees_are_written_in_indian_grouping(self):
        self.assertEqual([rupee_text(v) for v in (0, 1000, 232000, 1500000, Decimal("-82000.4"))],
                         ["₹0", "₹1,000", "₹2,32,000", "₹15,00,000", "-₹82,000"])


class AffordabilityAnswerTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("afford-synthetic", rent_or_emi="20000", country="India")

    def ask(self, text="Can I afford a 30000 rupee phone this month?", scope="general"):
        cache.clear()
        return hybrid_answer(None, self.user, text, scope=scope)

    def test_an_inr_balance_gives_months_of_cover_before_and_after(self):
        BankAccount.objects.create(user=self.user, account_number="SYN-1", currency="INR", current_balance="150000.00")
        result = self.ask()
        self.assertEqual((result["provider"], result["grounding"], result["narrative_withheld"]), ("local_evidence", "canonical_affordability", False))
        self.assertEqual([s["ref"] for s in result["sources"]], ["canonical-finance"])
        self.assertIn("You hold ₹1,50,000 in your bank accounts [canonical-finance].", result["answer"])
        self.assertIn("about ₹20,000 a month, so that covers about 7.5 months", result["answer"])
        self.assertIn("you would have ₹1,20,000, about 6.0 months", result["answer"])
        self.assertIn("this fits", result["answer"])
        self.assertIn("below it", self.ask("can I afford a 1 lakh holiday?")["answer"])
        self.assertIn("more than that", self.ask("can I afford 2 lakh?", scope="finance")["answer"])

    def test_an_unlabelled_balance_counts_as_rupees_for_an_owner_in_india_and_abroad_accounts_are_named(self):
        BankAccount.objects.create(user=self.user, account_number="SYN-2", current_balance="150000.00")  # currency not recorded
        BankAccount.objects.create(user=self.user, account_number="SYN-3", current_balance="2000.00", currency="USD")
        answer = self.ask()["answer"]
        self.assertIn("You hold ₹1,50,000 in your bank accounts", answer)
        self.assertIn("You also hold USD 2000.00 in other currencies; that is not counted here", answer)

    def test_an_unlabelled_balance_is_withheld_when_the_home_currency_is_unknown_or_not_inr(self):
        BankAccount.objects.create(user=self.user, account_number="SYN-2", current_balance="150000.00")
        for country, fix in (("", "Set your country in Settings"), ("Germany", "set its currency to INR")):
            get_user_model().objects.filter(pk=self.user.pk).update(country=country); self.user.refresh_from_db()
            with self.subTest(country=country), override_settings(TIME_ZONE="UTC"):
                answer = self.ask()["answer"]
                self.assertIn(fix, answer)
                self.assertNotIn("1,50,000", answer)
