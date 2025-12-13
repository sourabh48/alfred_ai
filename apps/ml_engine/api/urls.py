from django.urls import path
from .views import EmotionalSpendAPI,AlfredExplainAPI

urlpatterns = [
    path("emotion/", EmotionalSpendAPI.as_view()),
    path("explain/", AlfredExplainAPI.as_view()),
]
