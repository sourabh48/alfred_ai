from django.db import models
from django.conf import settings

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ("food", "Food"),
        ("shopping", "Shopping"),
        ("bills", "Bills"),
        ("travel", "Travel"),
        ("health", "Health"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.FloatField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    payment_mode = models.CharField(max_length=50, default="UPI")
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Alfred AI fields
    is_emotional = models.BooleanField(default=False)
    model_confidence = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user.username} | {self.category} | {self.amount}"
