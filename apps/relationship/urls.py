from django.urls import path
from .views import RelationshipListCreateView, RelationshipDetailView, relationship_alignment

urlpatterns = [
    path("", RelationshipListCreateView.as_view()),
    path("alignment/", relationship_alignment, name="relationship_alignment"),
    path("<int:pk>/", RelationshipDetailView.as_view()),
]
