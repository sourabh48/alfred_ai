"""Bounded local checkpoints; remote contact requires operator and owner opt-in."""
from pathlib import Path
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from alfred_ai.services.api_errors import safe_error_details
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from apps.ml_engine.services.knowledge_hub import KnowledgeHub
from apps.ml_engine.services.knowledge_git import configured_git, git_provider
from apps.ml_engine.services.memory_sync import remaining


class Command(BaseCommand):
    help = 'Checkpoint encrypted local learning; synchronize only approved knowledge packs.'

    def add_arguments(self, parser):
        parser.add_argument('--seconds', type=float, default=2)

    def handle(self, **options):
        seconds = options['seconds']
        if not 0 < seconds <= 5:
            raise CommandError('Checkpoint deadline must be between zero and five seconds.')
        if not (Path(settings.ALFRED_MEMORY_DIR) / 'verified.sqlite3').exists():
            return
        deadline = time.monotonic() + seconds
        try:
            store = MemoryStore(settings.ALFRED_MEMORY_DIR, timeout=remaining(deadline))
            users = get_user_model().objects.filter(is_active=True).order_by('pk')
            offset = (int(time.time() // 60) * 16) % max(users.count(), 1)
            for user in users[offset:offset + 16]:
                if time.monotonic() >= deadline:
                    break
                hub = KnowledgeHub(store, deadline=deadline)
                hub.checkpoint(user)
                with store._transaction(timeout=remaining(deadline)) as db:
                    _, policy = hub._state(db, _owner(user))
                    enabled = policy['enabled'] and policy['remote_consent']
                if enabled and configured_git():
                    try:
                        hub.sync(user, git_provider(store, deadline=deadline), seconds=remaining(deadline))
                    except Exception as exc:
                        safe_error_details(exc, 'Knowledge sync deferred; encrypted local updates remain queued.', logger_name=__name__)
        except Exception as exc:
            safe_error_details(exc, 'Knowledge checkpoint deferred; existing local data is preserved.', logger_name=__name__)
