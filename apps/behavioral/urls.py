from django.urls import path
from .views import BehavioralSignalListCreateView

urlpatterns = [
    path("", BehavioralSignalListCreateView.as_view()),
]
