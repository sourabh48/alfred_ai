from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "monthly_income", "city", "created_at")
    search_fields = ("username", "email", "city")
    list_filter = ("city", "country")
