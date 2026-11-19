"""Save a person's Gemini key locally through a masked prompt, without turning cloud answers on."""
from getpass import getpass, GetPassWarning
import sys
import warnings

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ml_engine.services.memory_reasoning import GeminiReasoner, _drop_openai
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner


class Command(BaseCommand):
    help="Encrypt a person's own Gemini key locally; cloud answers stay off until they opt in."

    def add_arguments(self,parser): parser.add_argument('--user',type=int,required=True)

    def handle(self,**options):
        if not sys.stdin.isatty(): raise CommandError('Use an interactive terminal with a masked credential prompt.')
        try:
            user=get_user_model().objects.get(pk=options['user'],is_active=True)
            with warnings.catch_warnings():
                warnings.simplefilter('error',GetPassWarning)
                key=getpass('Gemini API key (masked): ')
            GeminiReasoner(key)
            store=MemoryStore(settings.ALFRED_MEMORY_DIR)
            with store._transaction() as db:
                state=store._sync_state(db,_owner(user))
                if state.get('reasoning_policy',{}).get('enabled'): raise ValueError()
                _drop_openai(state); state['gemini_key']=key; store._write_sync_state(db,_owner(user),state)
        except Exception: raise CommandError('Reasoning credential was not saved; existing configuration is preserved.') from None
        self.stdout.write('Gemini key encrypted locally. Cloud answers stay off until the person opts in.')
