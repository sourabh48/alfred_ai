from django.urls import path
from .views import RiskSignalListCreateView, risk_outlook

urlpatterns = [
    path("", RiskSignalListCreateView.as_view()),
    path("outlook/", risk_outlook, name="risk_outlook"),
]
