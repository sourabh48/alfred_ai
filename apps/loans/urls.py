from django.urls import path
from .views import LoanListCreateView, LoanDetailView

urlpatterns = [
    path("", LoanListCreateView.as_view()),
    path("<int:pk>/", LoanDetailView.as_view()),
]
