from django.contrib import admin
from .models import CareerProfile

@admin.register(CareerProfile)
class CareerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "experience_years", "last_salary")
    search_fields = ("role", "skills")
