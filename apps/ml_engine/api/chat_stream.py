"""Session-only streaming for unsaved local general chat."""
from django.http import StreamingHttpResponse
from rest_framework.exceptions import Throttled

from .memory import MemoryAPI, memory_store
from .conversations import current_session
from ..services import hybrid_intelligence
from ..services.local_chat_stream import LocalChatStream, GenerationIncomplete, GenerationTimedOut, GenerationLimitReached


class LocalChatStreamAPI(MemoryAPI):
    def post(self,request):
        data = self.payload(('query','scope','cloud_consent','query_sensitivity','answer_style','page_context'))
        query = data.get('query')
        if (not isinstance(query,str) or not query.strip() or len(query.encode())>1024
                or data.get('scope','general') != 'general' or data.get('cloud_consent',False) is not False
                or data.get('query_sensitivity','sensitive') not in ('public','personal','sensitive')
                or not isinstance(data.get('page_context',[]),list)):
            raise ValueError('Streaming requires a bounded unsaved local general question.')
        hybrid_intelligence.answer_budget(query,'general',data.get('answer_style','auto'))
        hybrid_intelligence.validate_dialogue(data.get('page_context',[]),'general',False)
        current_session(request)
        def run(stream):
            store = memory_store()
            store.embedder.cancellation = stream
            result = hybrid_intelligence.hybrid_answer(store,request.user,query,scope='general',cloud_consent=False,
                query_sensitivity=data.get('query_sensitivity','sensitive'),
                answer_style=data.get('answer_style','auto'),conversation_context=data.get('page_context',[]),
                local=hybrid_intelligence.OllamaReasoner(stream=stream))
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
        if not stream.start(): raise Throttled(detail='Local generation is busy. Your draft is preserved; retry shortly.')
        response = StreamingHttpResponse(stream,content_type='application/x-ndjson')
        response['X-Accel-Buffering'] = 'no'
        return response
