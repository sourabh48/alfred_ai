from django.db import models
from django.conf import settings

class BehavioralSignal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stress_score = models.FloatField(default=0)
    sleep_hours = models.FloatField(default=0)
    work_hours = models.FloatField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"{self.user_id} stress {self.stress_score} at {self.timestamp}"
