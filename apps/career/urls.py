from django.urls import path
from .views import CareerJobMatchView, CareerProfileView, CareerProjectionSimulationView, CareerRecruiterMatchView, CareerResumeListView, CareerResumeUploadView, career_dashboard, career_projection

urlpatterns = [
    path("", CareerProfileView.as_view()),
    path("dashboard/", career_dashboard, name="career_dashboard"),
    path("projection/", career_projection, name="career_projection"),
    path("projection/simulate/", CareerProjectionSimulationView.as_view(), name="career_projection_simulation"),
    path("resumes/", CareerResumeListView.as_view(), name="career_resume_list"),
    path("resumes/upload/", CareerResumeUploadView.as_view(), name="career_resume_upload"),
    path("recruiter-match/", CareerRecruiterMatchView.as_view(), name="career_recruiter_match"),
    path("job-match/", CareerJobMatchView.as_view(), name="career_job_match"),
]
