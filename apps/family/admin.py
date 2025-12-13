from django.contrib import admin
from .models import Dependent

@admin.register(Dependent)
class DependentAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "age", "relation")
    list_filter = ("relation",)
