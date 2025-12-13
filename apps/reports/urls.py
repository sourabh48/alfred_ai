from django.urls import path
from .views import ReportListView

urlpatterns = [
    path("", ReportListView.as_view()),
]
