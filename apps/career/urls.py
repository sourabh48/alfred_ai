from django.urls import path
from .views import CareerProfileView

urlpatterns = [
    path("", CareerProfileView.as_view()),
]
