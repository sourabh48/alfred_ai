from django.db import models
from django.db.models import Q
from django.conf import settings

from alfred_ai.services.currency import CURRENCY_CHOICES, RUPEE
from .money import InvestmentMoneyField, investment_money, investment_total_float


class InvestmentQuerySet(models.QuerySet):
    def in_rupee_totals(self):
        """Positions that join rupee totals: INR, or never recorded (the legacy INR convention).

        Other currencies are reported as separate groups; there is no FX conversion.
        """
        return self.filter(Q(currency__isnull=True) | Q(currency=RUPEE))


class Investment(models.Model):
    ASSET_TYPES = [
        ("equity", "Equity"),
        ("debt", "Debt"),
        ("gold", "Gold"),
        ("reit", "REIT"),
        ("mutual_fund", "Mutual Fund"),
        ("crypto", "Crypto"),
        ("cash", "Cash / Liquid"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES)
    asset_name = models.CharField(max_length=120)
    institution = models.CharField(max_length=120, blank=True)
    account_number = models.CharField(max_length=64, blank=True)
    invested_amount = InvestmentMoneyField(max_digits=14, decimal_places=2, default=0)
    monthly_sip = InvestmentMoneyField(max_digits=14, decimal_places=2, default=0)
    current_value = InvestmentMoneyField(max_digits=14, decimal_places=2, default=0)
    # Denomination of the three amounts above; null means not recorded and is never guessed (FIN-15).
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, null=True, blank=True, default=None)
    annual_return_rate = models.FloatField(default=0)
    risk_level = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = InvestmentQuerySet.as_manager()

    class Meta:
        ordering = ["-current_value", "-id"]

    def __str__(self):
        return f"{self.user.username} - {self.asset_name}"

    @property
    def gain_loss(self) -> float:
        return investment_total_float(investment_money(self.current_value) - investment_money(self.invested_amount))


class InvestmentImportDocument(models.Model):
    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investment_import_documents")
    uploaded_file = models.FileField(upload_to="investment_imports/%Y/%m/")
    file_name = models.CharField(max_length=255)
    broker_name = models.CharField(max_length=120, blank=True)
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    extracted_text = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    linked_investments = models.ManyToManyField(Investment, blank=True, related_name="source_documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["user", "parser_status", "updated_at"]),
            models.Index(fields=["user", "broker_name", "updated_at"]),
        ]

    def __str__(self):
        broker = self.broker_name or "investment"
        return f"{self.user.username} - {broker} - {self.file_name}"


class InvestmentMoneySnapshot(models.Model):
    original_investment_id = models.PositiveBigIntegerField(unique=True)
    investment = models.ForeignKey(Investment, null=True, on_delete=models.SET_NULL, related_name="money_snapshots")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investment_money_snapshots")
    source_values = models.JSONField()
    normalized_values = models.JSONField()
    policy = models.CharField(max_length=30, default="investment-money-v1")
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class InvestmentDocumentEvidence(models.Model):
    document = models.ForeignKey(InvestmentImportDocument, on_delete=models.CASCADE, related_name="field_evidence")
    investment = models.ForeignKey(Investment, null=True, on_delete=models.SET_NULL, related_name="document_evidence")
    original_investment_id = models.PositiveBigIntegerField()
    source_values = models.JSONField(default=dict)
    reviewed_fields = models.JSONField(default=dict)
    review_generation = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("document", "original_investment_id"), name="investment_source_record_once")]


class ResearchDecision(models.Model):
    """An owner's dated research call on an instrument, kept apart from owned holdings (INVEST2-002).

    Mirrors the TradingAgents decision log (Apache-2.0, pin e8f5503e: memory/log.py, settlement.py, agents/rating.py),
    independently written: a five-tier rating stays pending until its review date, then the owner records the closing
    prices and a lesson. Prices are what the owner enters; nothing is fetched, traded or written to holdings.
    """
    RATINGS = [("buy", "Buy"), ("overweight", "Overweight"), ("hold", "Hold"), ("underweight", "Underweight"), ("sell", "Sell")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="research_decisions")
    instrument = models.CharField(max_length=120)
    rating = models.CharField(max_length=12, choices=RATINGS)
    thesis = models.TextField(max_length=4000)
    decided_on = models.DateField()
    review_on = models.DateField()
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, null=True, blank=True, default=None)
    entry_price = models.DecimalField(max_digits=18, decimal_places=4)
    benchmark = models.CharField(max_length=60, blank=True)
    benchmark_entry = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    settled_on = models.DateField(null=True, blank=True)
    exit_price = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    benchmark_exit = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    lesson = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-decided_on", "-id"]
        indexes = [models.Index(fields=["user", "instrument", "decided_on"])]

    def __str__(self):
        return f"{self.user.username} - {self.instrument} - {self.rating}"
