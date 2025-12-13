from django.urls import path
from .views import RiskSignalListCreateView

urlpatterns = [
    path("", RiskSignalListCreateView.as_view()),
]
