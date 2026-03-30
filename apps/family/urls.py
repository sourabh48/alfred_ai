from django.urls import path
from .views import DependentListCreateView, DependentDetailView, family_growth

urlpatterns = [
    path("", DependentListCreateView.as_view()),
    path("growth/", family_growth, name="family_growth"),
    path("<int:pk>/", DependentDetailView.as_view()),
]
