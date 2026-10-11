"""Provision a masked owner credential locally without enabling paid requests."""
from getpass import getpass, GetPassWarning
import sys
import warnings

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ml_engine.services.memory_reasoning import OpenAIReasoner
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner


class Command(BaseCommand):
    help='Encrypt an owner-specific OpenAI credential locally; reasoning stays disabled.'

    def add_arguments(self,parser): parser.add_argument('--user',type=int,required=True)

    def handle(self,**options):
        if not sys.stdin.isatty(): raise CommandError('Use an interactive terminal with a masked credential prompt.')
        try:
            user=get_user_model().objects.get(pk=options['user'],is_active=True)
            with warnings.catch_warnings():
                warnings.simplefilter('error',GetPassWarning)
                key=getpass('Restricted OpenAI project key (masked): ')
            OpenAIReasoner(key)
            store=MemoryStore(settings.ALFRED_MEMORY_DIR)
            with store._transaction() as db:
                state=store._sync_state(db,_owner(user))
                if state.get('reasoning_policy',{}).get('enabled'): raise ValueError()
                state['openai_key']=key; store._write_sync_state(db,_owner(user),state)
        except Exception: raise CommandError('Reasoning credential was not saved; existing configuration is preserved.') from None
        self.stdout.write('Owner credential encrypted locally. Paid requests and reasoning policy remain disabled.')
