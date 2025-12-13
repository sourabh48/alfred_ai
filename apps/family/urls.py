from django.urls import path
from .views import DependentListCreateView, DependentDetailView

urlpatterns = [
    path("", DependentListCreateView.as_view()),
    path("<int:pk>/", DependentDetailView.as_view()),
]
