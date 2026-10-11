from django.urls import path
from .views import (
    DependentDetailView,
    DependentListCreateView,
    FamilyAccountLinkAcceptView,
    FamilyAccountLinkListCreateView,
    FamilyAccountLinkRevokeView,
    FamilyFinancialSharingView,
    family_growth,
)

urlpatterns = [
    path("", DependentListCreateView.as_view()),
    path("growth/", family_growth, name="family_growth"),
    path("account-links/", FamilyAccountLinkListCreateView.as_view(), name="family_account_links"),
    path("account-links/accept/", FamilyAccountLinkAcceptView.as_view(), name="family_account_link_accept"),
    path("account-links/<int:pk>/revoke/", FamilyAccountLinkRevokeView.as_view(), name="family_account_link_revoke"),
    path("account-links/<int:pk>/financial-sharing/", FamilyFinancialSharingView.as_view(), name="family_financial_sharing"),
    path("<int:pk>/", DependentDetailView.as_view()),
]
