from django.urls import path
from .history_review_api import CareerHistoryReviewAPI
from .views import CareerApplicationKitView, CareerPlanCheckView, CareerPracticeFeedbackView, CareerBatchTriageView, CareerBulletRewriteView, CareerInterviewNotesView, career_story_bank, CareerSendEmailView, CareerOfferPrepView, CareerTriageView, career_patterns, career_triage_brief, CareerApplicationView, CareerJobMatchView, CareerMatchRecheckView, CareerJobOutcomeView, CareerResumeCompareView, career_follow_ups, CareerOpportunityListView, CareerProfileView, CareerProjectionSimulationView, CareerRecruiterMatchView, CareerResumeListView, CareerResumeUploadView, CareerResumeUseDetailsView, career_dashboard, career_projection

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
    path("job-analyses/<int:pk>/recheck-match/", CareerMatchRecheckView.as_view(), name="career_match_recheck"),
    path("follow-ups/", career_follow_ups, name="career_follow_ups"),
    path("resumes/compare/", CareerResumeCompareView.as_view(), name="career_resume_compare"),
    path("job-analyses/", CareerOpportunityListView.as_view(), name="career_opportunities"),
    path("job-analyses/<int:pk>/triage/", CareerTriageView.as_view(), name="career_job_triage"),
    path("job-analyses/<int:pk>/kit/", CareerApplicationKitView.as_view(), name="career_job_kit"),
    path("job-analyses/<int:pk>/rewrite-bullets/", CareerBulletRewriteView.as_view(), name="career_job_rewrite_bullets"),
    path("job-analyses/<int:pk>/email/<str:action>/", CareerSendEmailView.as_view(), name="career_job_email"),
    path("job-analyses/<int:pk>/offer-prep/", CareerOfferPrepView.as_view(), name="career_job_offer_prep"),
    path("triage/batch/", CareerBatchTriageView.as_view(), name="career_batch_triage"),
    path("triage-brief/", career_triage_brief, name="career_triage_brief"),
    path("patterns/", career_patterns, name="career_patterns"),
    path("plan-check/<str:kind>/", CareerPlanCheckView.as_view(), name="career_plan_check"),
    path("job-analyses/<int:pk>/practice-feedback/", CareerPracticeFeedbackView.as_view(), name="career_practice_feedback"),
    path("job-analyses/<int:pk>/interview-notes/", CareerInterviewNotesView.as_view(), name="career_job_interview_notes"),
    path("stories/", career_story_bank, name="career_story_bank"),
]
