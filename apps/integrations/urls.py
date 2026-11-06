"""
URL Configuration for Integrations app
"""
from django.urls import path
from . import views

# Credit score and credit report routes were removed on 2026-11-06 by owner decision (FIN-17 dropped).
urlpatterns = [
    path('recommendations/overview/', views.recommendation_overview, name='recommendation_overview'),
    path('tax/overview/', views.tax_optimizer_overview, name='tax_optimizer_overview'),
]
