from django.urls import path
from .statements import StatementEvidenceAPI
from .investment_evidence import InvestmentEvidenceAPI
from .loan_evidence import LoanEvidenceAPI
from .financial_evidence import FinancialEvidenceAPI, FinancialSourcePageAPI, ClosureEvidenceAPI, DocumentRecordPageAPI, DocumentKnowledgeSearchAPI
from .views import AlfredExplainAPI, AlfredPersonalInsightsAPI, EmotionalSpendAPI, MLRuntimeControlAPI, MLRuntimeStatusAPI
from .memory import MemoryCollectionAPI, MemoryDetailAPI, MemoryRetentionAPI, MemoryResetAPI, MemoryRestoreAPI, MemoryRetrieveAPI, MemorySyncAPI, MemoryReasoningAPI, MemoryLearningAPI
from .conversations import ConversationPolicyAPI, ConversationCollectionAPI, ConversationDetailAPI, ConversationClearAPI
from .document_corpus import DocumentCorpusAPI, DocumentCorpusSearchAPI, DocumentCorpusDetailAPI, DocumentCorpusUploadAPI, DocumentCorpusOriginalAPI, DocumentCorpusQuestionAPI

urlpatterns = [
    path('document-corpus/', DocumentCorpusAPI.as_view()),
    path('document-corpus/search/', DocumentCorpusSearchAPI.as_view()),
    path('document-corpus/question/', DocumentCorpusQuestionAPI.as_view()),
    path('document-corpus/upload/', DocumentCorpusUploadAPI.as_view()),
    path('document-corpus/<str:identity>/original/', DocumentCorpusOriginalAPI.as_view()),
    path('document-corpus/<str:identity>/', DocumentCorpusDetailAPI.as_view()),
    path('financial-documents/<str:kind>/<int:document_id>/search/', DocumentKnowledgeSearchAPI.as_view()),
    path('financial-documents/<str:kind>/', DocumentRecordPageAPI.as_view()),
    path('financial-documents/<str:kind>/<int:document_id>/', DocumentRecordPageAPI.as_view()),
    path('loan-evidence/<int:document_id>/<int:identity>/', LoanEvidenceAPI.as_view()),
    path('investment-evidence/<int:document_id>/<int:identity>/', InvestmentEvidenceAPI.as_view()),
    path('closure-evidence/<int:identity>/', ClosureEvidenceAPI.as_view()),
    path('financial-evidence/', FinancialEvidenceAPI.as_view()),
    path('financial-evidence/<str:kind>/<int:identity>/documents/', FinancialSourcePageAPI.as_view()),
    path('financial-evidence/<str:kind>/<int:identity>/', FinancialEvidenceAPI.as_view()),
    path('statement-evidence/', StatementEvidenceAPI.as_view()),
    path('statement-evidence/<int:identity>/', StatementEvidenceAPI.as_view()),
    path("conversations/policy/", ConversationPolicyAPI.as_view()),
    path("conversations/clear/", ConversationClearAPI.as_view()),
    path("conversations/", ConversationCollectionAPI.as_view()),
    path("conversations/<str:identity>/", ConversationDetailAPI.as_view()),
    path("memories/", MemoryCollectionAPI.as_view()),
    path("memories/reset/", MemoryResetAPI.as_view()),
    path("memories/retention/", MemoryRetentionAPI.as_view()),
    path("memories/restore/", MemoryRestoreAPI.as_view()),
    path("memories/retrieve/", MemoryRetrieveAPI.as_view()),
    path("memories/sync/", MemorySyncAPI.as_view()),
    path("memories/reason/", MemoryReasoningAPI.as_view()),
    path("memories/learning/", MemoryLearningAPI.as_view()),
    path("memories/<str:identity>/", MemoryDetailAPI.as_view()),
    path("emotion/", EmotionalSpendAPI.as_view()),
    path("explain/", AlfredExplainAPI.as_view()),
    path("personal-insights/", AlfredPersonalInsightsAPI.as_view()),
    path("runtime-status/", MLRuntimeStatusAPI.as_view()),
    path("runtime-control/", MLRuntimeControlAPI.as_view()),
]
