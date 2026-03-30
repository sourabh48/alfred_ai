from django.urls import path
from .views import ReportListView, SystemTicketListCreateView, SystemTicketDetailView

urlpatterns = [
    path("", ReportListView.as_view()),
    path("tickets/", SystemTicketListCreateView.as_view(), name="system_ticket_list_create"),
    path("tickets/<int:pk>/", SystemTicketDetailView.as_view(), name="system_ticket_detail"),
]
