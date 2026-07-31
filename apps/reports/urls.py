from django.urls import path
from .views import ChatGPTImportListCreateView, ReportListView, SystemTicketListCreateView, SystemTicketDetailView

urlpatterns = [
    path("", ReportListView.as_view()),
    path("chatgpt-imports/", ChatGPTImportListCreateView.as_view(), name="chatgpt_import_list_create"),
    path("tickets/", SystemTicketListCreateView.as_view(), name="system_ticket_list_create"),
    path("tickets/<int:pk>/", SystemTicketDetailView.as_view(), name="system_ticket_detail"),
]
