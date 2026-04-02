from django.urls import path
from .views import AlfredExplainAPI, AlfredPersonalInsightsAPI, EmotionalSpendAPI, MLRuntimeControlAPI, MLRuntimeStatusAPI

urlpatterns = [
    path("emotion/", EmotionalSpendAPI.as_view()),
    path("explain/", AlfredExplainAPI.as_view()),
    path("personal-insights/", AlfredPersonalInsightsAPI.as_view()),
    path("runtime-status/", MLRuntimeStatusAPI.as_view()),
    path("runtime-control/", MLRuntimeControlAPI.as_view()),
]
