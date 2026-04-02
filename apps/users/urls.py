from django.urls import path
from .views import UserDataResetView, UserProfileView

urlpatterns = [
    path("profile/", UserProfileView.as_view()),
    path("profile/clear-data/", UserDataResetView.as_view()),
]
