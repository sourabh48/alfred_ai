"""How rupee amounts are written. Recognising one never converts it to another currency."""
import hashlib
from decimal import Decimal

from django.db import models

# Use with re.IGNORECASE. The odd sign is the UTF-8 rupee sign misread as Windows-1252.
INR_NAME = r"(?:INR\.?|RUPEES?|RS(?:\.?/-|\.)?)"
INR_SIGN = r"(?:\u20b9|\u00e2\u201a\u00b9|\u20a8)"
# After a label the name can touch the word before it, as in "Loan AmountRs.5,00,000".
INR_LABEL_TOKEN = rf"(?:{INR_NAME}|{INR_SIGN})"
INR_TOKEN = rf"(?:\b{INR_NAME}|{INR_SIGN})"
# A number with no prefix is money only when a currency name follows it. A bare "/-" also ends
# other currencies and references, so it counts only after a label.
INR_AMOUNT = (
    rf"(?:{INR_TOKEN}\s*|(?<![0-9A-Za-z,.$\u20ac\u00a3])(?=[0-9][0-9,]*(?:\.\d{{1,2}})?\s*(?:RUPEES?|INR|RS)\b))"
    r"([0-9][0-9,]*(?:\.\d{1,2})?)(?!\.?\d)"
)

# FIN-15 registry (owner-approved contract, 2026-11-06). A record carries one of these ISO 4217
# codes or null ("not recorded"); unknown is never guessed or backfilled. Calculations never use FX;
# amounts in different currencies are grouped, never added together (display-only approximations: exchange_rates).
REGISTRY_VERSION = "fin15-v1"
RUPEE = "INR"
# code -> (label, ISO minor unit); every unit fits the existing 14,2 money storage.
CURRENCIES = {
    "INR": ("Indian rupee", 2),
    "USD": ("US dollar", 2),
    "EUR": ("Euro", 2),
    "GBP": ("Pound sterling", 2),
}
CURRENCY_CHOICES = [(code, f"{label} ({code})") for code, (label, _) in CURRENCIES.items()]


def currency_status(code) -> str:
    return "recorded" if code else "not_recorded"


def counts_in_rupees(code) -> bool:
    """Not recorded keeps the legacy INR convention; any other recorded code stays out of rupee maths."""
    return not code or code == RUPEE


def rupee_amount(amount, code):
    """The amount for rupee calculations, or zero when it is recorded in another currency. Never converted."""
    return amount if counts_in_rupees(code) else Decimal("0.00")


def currency_fingerprint(*querysets, fields=("currency",)):
    """Changes whenever a recorded currency changes, so cached totals rebuild. Only recorded rows are read."""
    digest = hashlib.sha256()
    for queryset in querysets:
        for field in fields:
            if field in {f.name for f in queryset.model._meta.fields}:
                rows = queryset.exclude(**{f"{field}__isnull": True}).order_by("pk").values_list("pk", field)
                digest.update(f"{queryset.model._meta.label}.{field}:{list(rows)}".encode())
    return digest.hexdigest()[:16]


def currency_field():
    return models.CharField(max_length=3, choices=CURRENCY_CHOICES, null=True, blank=True, default=None)


class CurrencyQuerySet(models.QuerySet):
    """For models whose amounts share one `currency` column (FIN-15)."""

    def in_rupee_totals(self):
        return self.filter(models.Q(currency__isnull=True) | models.Q(currency=RUPEE))

    def in_other_currencies(self):
        return self.exclude(currency__isnull=True).exclude(currency=RUPEE)
