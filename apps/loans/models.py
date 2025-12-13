from django.db import models
from django.conf import settings

class Loan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    loan_type = models.CharField(max_length=50)
    principal = models.FloatField()
    interest_rate = models.FloatField()
    emi = models.FloatField()
    start_date = models.DateField()

    def __str__(self):
        return f"{self.user.username} {self.loan_type}"
