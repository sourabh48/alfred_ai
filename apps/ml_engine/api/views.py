from time import monotonic

from apps.ml_engine.core.alfred_router import alfred_router
from apps.ml_engine.runtime_control import build_runtime_status, grant_training_consent, revoke_training_consent
from apps.ml_engine.training.orchestrator import run_training_cycle, training_health_snapshot
from apps.expenses.services.financial_intelligence import build_financial_intelligence

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.ml_engine.behavior.behavior_signature import behavior_signature
from apps.ml_engine.behavior.anomaly_detector import anomaly_detector
from apps.ml_engine.behavior.personalizer import personalizer
from apps.ml_engine.behavior.insight_generator import insight_generator
from .memory import MemoryAPI, memory_store
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer, OllamaReasoner
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable

class EmotionalSpendAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data.copy()
        payload["user"] = request.user
        result = alfred_router.route("emotional-spend", payload)
        return Response(result)

class AlfredExplainAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payload = request.data

        expenses = payload.get("expenses", [])
        stress = payload.get("stress", [])
        prediction = payload.get("prediction", 0)

        sig = behavior_signature.generate_signature(expenses, stress)

        expense_spike, amount = anomaly_detector.detect_expense_spike(expenses)
        anomalies = {
            "expense_spike": expense_spike,
            "spike_amount": amount
        }

        insights = insight_generator.generate_insights(sig, anomalies)

        tone = personalizer.personalize_ai_tone(sig["stress_avg"])

        return Response({
            "signature": sig,
            "anomalies": anomalies,
            "insights": insights,
            "recommended_tone": tone
        })


class AlfredPersonalInsightsAPI(MemoryAPI):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.loans.models import LoanClosureDocument
        from apps.expenses.services.statement_evidence import choices
        from apps.ml_engine.services.canonical_evidence import choices as financial_choices
        intelligence = {} if request.query_params.get('assistant_status') == '1' else dict(build_financial_intelligence(request.user))
        intelligence['assistant_documents']=[{'id':identity,'label':f'Verified loan closure #{identity}'} for identity in
            LoanClosureDocument.objects.filter(loan__user=request.user,verification_status='verified').order_by('-id').values_list('id',flat=True)[:20]]
        intelligence['assistant_statement_records']=choices(request.user)
        intelligence['assistant_financial_records']=financial_choices(request.user)
        if request.query_params.get('assistant_status') == '1':
            try:
                OllamaReasoner()._digest(deadline=monotonic()+1)
                intelligence['local_model_status'] = 'available'
            except EmbeddingUnavailable:
                intelligence['local_model_status'] = 'unavailable'
        return Response(intelligence)

    def post(self,request):
        data=self.payload(('query','scope','document_id','transaction_id','record_type','record_id','selected_documents','source_catalog','selected_records','cloud_consent','query_sensitivity',
                           'conversation_id','conversation_revision','request_id'))
        document_question=data.get('scope')=='financial_document'
        if document_question:
            from .conversations import current_session
            current_session(request)
            if data.get('conversation_id') is not None: raise ValueError('Document-question persistence is not supported.')
        store = None if document_question else memory_store()
        identity = data.get('conversation_id')
        history_fields = {'conversation_id','conversation_revision','request_id'}
        if identity is None and history_fields & set(data): raise ValueError()
        if identity is not None:
            from .conversations import current_session
            from ..services.conversation_history import ConversationHistory, ConversationPermission
            if data.get('cloud_consent', False) is not False: raise ConversationPermission()
            current_session(request)
            history = ConversationHistory(store)
            question = dict(query=data.get('query'), scope=data.get('scope','general'), document_id=data.get('document_id'))
            if 'transaction_id' in data: question['transaction_id']=data['transaction_id']
            for key in ('record_type','record_id','selected_documents','source_catalog'):
                if key in data: question[key]=data[key]
            generation, saved = history.prepare(request.user, identity, data.get('conversation_revision'), data.get('request_id'), question)
            if saved:
                record = history.get(request.user, identity)
                current_session(request)
                return Response({**saved, 'historical':True, 'conversation':{'id':identity, 'revision':record['revision']}})
        try:
            result = hybrid_answer(store,request.user,data.get('query'),scope=data.get('scope','general'),
                document_id=data.get('document_id'),transaction_id=data.get('transaction_id'),record_type=data.get('record_type'),record_id=data.get('record_id'),
                selected_documents=data.get('selected_documents'),source_catalog=data.get('source_catalog'),selected_records=data.get('selected_records'),cloud_consent=data.get('cloud_consent',False),
                query_sensitivity=data.get('query_sensitivity','sensitive'))
        finally:
            if document_question: current_session(request)
        if identity is not None:
            current_session(request)
            revision = data.get('conversation_revision')
            if result['provider']!='local_evidence':
                revision = history.append(request.user, identity, revision, data.get('request_id'), question, result, generation)
            result = {**result, 'conversation':{'id':identity, 'revision':revision}, 'conversation_saved':result['provider']!='local_evidence'}
        return Response(result)


class MLRuntimeStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = build_runtime_status(request.user)
        payload["training_health"] = training_health_snapshot()
        return Response(payload)


class MLRuntimeControlAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can manage ALFRED training startup.")

        action = str(request.data.get("action") or "").strip().lower()
        if action == "approve":
            grant_training_consent(request.user)
            return Response(
                {
                    "detail": "ALFRED startup auto-training has been approved for this environment.",
                    "status": build_runtime_status(request.user),
                }
            )
        if action == "revoke":
            revoke_training_consent(request.user)
            return Response(
                {
                    "detail": "ALFRED startup auto-training approval has been revoked.",
                    "status": build_runtime_status(request.user),
                }
            )
        if action == "run_now":
            status = build_runtime_status(request.user)
            if not status["approval"]["granted"]:
                raise ValidationError({"detail": "Approve startup training first."})
            if not status["runtime"]["ready"]:
                raise ValidationError({"detail": status["runtime"]["reason"] or "Training runtime is unavailable."})
            result = run_training_cycle(trigger="superuser_manual", force=True)
            return Response(
                {
                    "detail": "ALFRED training cycle finished.",
                    "status": build_runtime_status(request.user),
                    "training_result": result,
                }
            )
        raise ValidationError({"detail": "Unsupported action."})
