"""
URL Configuration for Integrations app
"""
from django.urls import path
from . import views

urlpatterns = [
    # Credit Score endpoints
    path('credit-score/', views.get_credit_score, name='get_credit_score'),
    path('credit-score/all-bureaus/', views.get_all_bureau_scores, name='all_bureau_scores'),
    path('credit-score/factors/', views.analyze_credit_factors, name='credit_factors'),
    path('credit-score/trend/', views.get_credit_score_trend, name='credit_trend'),
    path('credit-score/improvement-plan/', views.get_improvement_plan, name='improvement_plan'),
    path('credit-score/peer-comparison/', views.compare_with_peers, name='peer_comparison'),
    path('credit-score/comprehensive-report/', views.comprehensive_credit_report, name='comprehensive_report'),
    path('credit-score/refresh/', views.refresh_credit_score, name='refresh_credit_score'),
    path('recommendations/overview/', views.recommendation_overview, name='recommendation_overview'),
    path('tax/overview/', views.tax_optimizer_overview, name='tax_optimizer_overview'),
]
