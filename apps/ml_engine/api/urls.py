from django.urls import path
from .views import AlfredExplainAPI, AlfredPersonalInsightsAPI, EmotionalSpendAPI

urlpatterns = [
    path("emotion/", EmotionalSpendAPI.as_view()),
    path("explain/", AlfredExplainAPI.as_view()),
    path("personal-insights/", AlfredPersonalInsightsAPI.as_view()),
]
