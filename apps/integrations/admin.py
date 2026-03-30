from django.contrib import admin

from .models import CreditScore, CreditScoreFactor, EmailConnection, VerifiedExternalInsight


admin.site.register(CreditScore)
admin.site.register(CreditScoreFactor)
admin.site.register(EmailConnection)
admin.site.register(VerifiedExternalInsight)
