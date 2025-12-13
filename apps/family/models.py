from django.db import models
from django.conf import settings

class Dependent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    relation = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.relation})"
