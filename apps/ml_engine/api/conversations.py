"""Session-only conversation lifecycle; there is no cloud/history export endpoint."""
from importlib import import_module
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth import get_user
from rest_framework.response import Response

from .memory import MemoryAPI, memory_store
from ..services.conversation_history import ConversationHistory, ConversationPermission
from ..services.persistent_memory import _owner


def current_session(request):
    session_key = request.session.session_key
    if not session_key: raise ConversationPermission()
    fresh = import_module(settings.SESSION_ENGINE).SessionStore(session_key=session_key)
    user = get_user(SimpleNamespace(session=fresh))
    if not user.is_authenticated or _owner(user) != _owner(request.user):
        # Prevent SAVE_EVERY_REQUEST from reviving an expired/logged-out session after inference.
        request.session.flush()
        raise ConversationPermission()


class ConversationPolicyAPI(MemoryAPI):
    def get(self, request):
        return Response({'policy': ConversationHistory(memory_store()).policy(request.user)})

    def put(self, request):
        data = self.payload(('enabled', 'consent', 'days'))
        return Response({'policy': ConversationHistory(memory_store()).configure(request.user,
            enabled=data.get('enabled'), consent=data.get('consent', False), days=data.get('days'))})


class ConversationCollectionAPI(MemoryAPI):
    def get(self, request):
        history = ConversationHistory(memory_store()); policy = history.policy(request.user)
        records = history.list(request.user) if policy['available'] and policy['enabled'] else []
        return Response({'policy': policy, 'conversations': records})

    def post(self, request):
        data = self.payload(('title',))
        return Response(ConversationHistory(memory_store()).create(request.user, data.get('title')), status=201)


class ConversationDetailAPI(MemoryAPI):
    def get(self, request, identity):
        record = ConversationHistory(memory_store()).get(request.user, identity)
        return Response(record) if record else Response({'detail':'Conversation was not found.'}, status=404)

    def delete(self, request, identity):
        if not ConversationHistory(memory_store()).delete(request.user, identity):
            return Response({'detail':'Conversation was not found.'}, status=404)
        return Response(status=204)


class ConversationClearAPI(MemoryAPI):
    def post(self, request):
        data = self.payload(('confirm',))
        if data.get('confirm') is not True: raise ValueError()
        return Response({'deleted': ConversationHistory(memory_store()).clear(request.user)})
