from django.urls import path
from .views import AlfredExplainAPI, AlfredPersonalInsightsAPI, EmotionalSpendAPI, MLRuntimeControlAPI, MLRuntimeStatusAPI
from .memory import MemoryCollectionAPI, MemoryDetailAPI, MemoryRetentionAPI, MemoryResetAPI, MemoryRestoreAPI, MemoryRetrieveAPI, MemorySyncAPI, MemoryReasoningAPI

urlpatterns = [
    path("memories/", MemoryCollectionAPI.as_view()),
    path("memories/reset/", MemoryResetAPI.as_view()),
    path("memories/retention/", MemoryRetentionAPI.as_view()),
    path("memories/restore/", MemoryRestoreAPI.as_view()),
    path("memories/retrieve/", MemoryRetrieveAPI.as_view()),
    path("memories/sync/", MemorySyncAPI.as_view()),
    path("memories/reason/", MemoryReasoningAPI.as_view()),
    path("memories/<str:identity>/", MemoryDetailAPI.as_view()),
    path("emotion/", EmotionalSpendAPI.as_view()),
    path("explain/", AlfredExplainAPI.as_view()),
    path("personal-insights/", AlfredPersonalInsightsAPI.as_view()),
    path("runtime-status/", MLRuntimeStatusAPI.as_view()),
    path("runtime-control/", MLRuntimeControlAPI.as_view()),
]
