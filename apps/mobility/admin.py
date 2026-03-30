from django.contrib import admin

from .models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord, TravelPlan, TripLog, TripPhoto


admin.site.register(BikeProfile)
admin.site.register(BikeServiceRecord)
admin.site.register(BikeIssueReport)
admin.site.register(BikeDocument)
admin.site.register(BikeConditionSnapshot)
admin.site.register(TravelPlan)
admin.site.register(TripLog)
admin.site.register(TripPhoto)
