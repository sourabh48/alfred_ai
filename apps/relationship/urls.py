from django.urls import path
from .views import RelationshipListCreateView, RelationshipDetailView

urlpatterns = [
    path("", RelationshipListCreateView.as_view()),
    path("<int:pk>/", RelationshipDetailView.as_view()),
]
