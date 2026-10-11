"""Masked local provisioning only; never enables synchronization or cloud contact."""
from getpass import getpass
import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ml_engine.services.memory_cloud import validate_profile
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner


class Command(BaseCommand):
    help='Save an owner-restricted S3 profile encrypted locally; real contact remains disabled.'

    def add_arguments(self,parser):
        parser.add_argument('--user',type=int,required=True)
        parser.add_argument('--bucket',required=True)
        parser.add_argument('--region',required=True)
        parser.add_argument('--account',required=True)

    def handle(self,**options):
        if not sys.stdin.isatty(): raise CommandError('Use an interactive terminal with masked credential prompts.')
        try:
            user=get_user_model().objects.get(pk=options['user'],is_active=True)
            profile=validate_profile({k:options[k] for k in ('bucket','region','account')}|{
                'access_key':getpass('Restricted access key (masked): '),'secret_key':getpass('Restricted secret key (masked): '),
                'session_token':getpass('Temporary session token, blank for no token (masked): ')})
            store=MemoryStore(settings.ALFRED_MEMORY_DIR)
            with store._transaction() as db:
                state=store._sync_state(db,_owner(user)); old=state.get('cloud')
                if state['enabled'] or (state['revision'] and (not old or any(old[k]!=profile[k] for k in ('bucket','region','account')))):
                    raise ValueError()
                state['cloud']=profile; store._write_sync_state(db,_owner(user),state)
        except Exception: raise CommandError('Cloud profile was not saved; existing configuration is preserved.') from None
        self.stdout.write('Restricted owner profile encrypted locally. Cloud contact and consent remain disabled.')
