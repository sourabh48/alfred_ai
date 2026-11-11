from django.urls import path
from .history_review_api import CareerHistoryReviewAPI
from .views import CareerApplicationView, CareerJobMatchView, CareerJobOutcomeView, CareerResumeCompareView, career_follow_ups, CareerOpportunityListView, CareerProfileView, CareerProjectionSimulationView, CareerRecruiterMatchView, CareerResumeListView, CareerResumeUploadView, CareerResumeUseDetailsView, career_dashboard, career_projection

urlpatterns = [
    path('job-analyses/<int:pk>/history-review/', CareerHistoryReviewAPI.as_view()),
    path("", CareerProfileView.as_view()),
    path("dashboard/", career_dashboard, name="career_dashboard"),
    path("projection/", career_projection, name="career_projection"),
    path("projection/simulate/", CareerProjectionSimulationView.as_view(), name="career_projection_simulation"),
    path("resumes/", CareerResumeListView.as_view(), name="career_resume_list"),
    path("resumes/upload/", CareerResumeUploadView.as_view(), name="career_resume_upload"),
    path("resumes/<int:pk>/use-details/", CareerResumeUseDetailsView.as_view(), name="career_resume_use_details"),
    path("recruiter-match/", CareerRecruiterMatchView.as_view(), name="career_recruiter_match"),
    path("job-match/", CareerJobMatchView.as_view(), name="career_job_match"),
    path("job-analyses/<int:pk>/outcome/", CareerJobOutcomeView.as_view(), name="career_job_outcome"),
    path("job-analyses/<int:pk>/application/", CareerApplicationView.as_view(), name="career_job_application"),
    path("follow-ups/", career_follow_ups, name="career_follow_ups"),
    path("resumes/compare/", CareerResumeCompareView.as_view(), name="career_resume_compare"),
    path("job-analyses/", CareerOpportunityListView.as_view(), name="career_opportunities"),
]
