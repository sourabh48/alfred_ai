from django.db import models
from django.conf import settings

class CareerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    experience_years = models.FloatField()
    skills = models.TextField()
    last_salary = models.FloatField(default=0)

    def __str__(self):
        return self.role
