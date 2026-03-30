from django.urls import path
from .views import BehavioralSignalListCreateView, behavioral_fingerprint, behavioral_stress

urlpatterns = [
    path("", BehavioralSignalListCreateView.as_view()),
    path("fingerprint/", behavioral_fingerprint, name="behavioral_fingerprint"),
    path("stress/", behavioral_stress, name="behavioral_stress"),
]
