"""Session-only cancellable local chat; domain output waits for source validation."""
from django.http import StreamingHttpResponse
from rest_framework.exceptions import Throttled

from .memory import MemoryAPI
from .conversations import current_session
from ..services import hybrid_intelligence
from ..services.local_chat_stream import LocalChatStream, GenerationIncomplete, GenerationTimedOut, GenerationLimitReached
from ..services.memory_sync import valid_id


class LocalChatStreamAPI(MemoryAPI):
    def post(self,request):
        data = self.payload(('query','scope','cloud_consent','query_sensitivity','answer_style','page_context',
            'conversation_id','conversation_revision','request_id','document_id','transaction_id',
            'record_type','record_id','selected_documents','source_catalog'))
        scope = data.get('scope','general')
        history_fields = {'conversation_id','conversation_revision','request_id'}
        saved = bool(history_fields & set(data))
        if saved and (not history_fields <= set(data) or 'page_context' in data
                or not valid_id(data['conversation_id']) or not valid_id(data['request_id'])
                or type(data['conversation_revision']) is not int or data['conversation_revision'] < 0):
            raise ValueError('Choose the current saved conversation and request identity.')
        query = data.get('query')
        if (not isinstance(query,str) or not query.strip() or len(query.encode())>1024
                or scope not in ('general','finance','financial_records','bank_statements','documents','travel')
                or data.get('cloud_consent',False) is not False
                or data.get('query_sensitivity','sensitive') not in ('public','personal','sensitive')
                or not isinstance(data.get('page_context',[]),list)
                or ('page_context' in data and scope != 'general')):
            raise ValueError('Streaming requires a bounded local question and its supported source.')
        hybrid_intelligence.answer_budget(query,scope,data.get('answer_style','auto'))
        hybrid_intelligence.validate_dialogue(data.get('page_context',[]),scope,False)
        current_session(request)
        def run(stream):
            from .views import AlfredPersonalInsightsAPI
            result = AlfredPersonalInsightsAPI().answer(request, data, stream=stream).data
            stream.check(); current_session(request)
            return result
        def error(exc):
            response = self.handle_exception(exc)
            payload = dict(response.data,status=response.status_code)
            if isinstance(exc,GenerationIncomplete):
                payload.update(code='local_stream_incomplete',detail='Local output is incomplete and unverified. Your draft is preserved; retry when ready.')
            if isinstance(exc,GenerationTimedOut):
                payload.update(code='local_stream_timeout',status=504,detail='Local generation exceeded its deadline. Your draft is preserved; choose Concise or narrow the question before retrying.')
            if isinstance(exc,GenerationLimitReached):
                payload.update(code='local_output_limit',status=422,detail='Local output reached its length limit before completion. Choose Concise or narrow the question. Nothing was saved; your draft is preserved.')
            return payload
        stream = LocalChatStream(run,error,lambda: current_session(request))
        stream.allow_preview = scope == 'general'
        if not stream.start(): raise Throttled(detail='Local generation is busy. Your draft is preserved; retry shortly.')
        response = StreamingHttpResponse(stream,content_type='application/x-ndjson')
        response['X-Accel-Buffering'] = 'no'
        return response
