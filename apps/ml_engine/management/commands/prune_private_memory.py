from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Revoke expired private memory keys without printing memory contents.'

    def handle(self, **options):
        if not (Path(settings.ALFRED_MEMORY_DIR) / 'verified.sqlite3').exists():
            self.stdout.write('Expired memories revoked: 0')
            return
        try:
            from apps.ml_engine.services.persistent_memory import MemoryStore
            count = MemoryStore(settings.ALFRED_MEMORY_DIR).expire_all()
        except Exception as exc:
            from alfred_ai.services.api_errors import safe_error_details
            error = safe_error_details(exc, 'Private memory cleanup is unavailable.', logger_name=__name__)
            raise CommandError('Private memory cleanup failed. Reference: ' + error['error_id']) from None
        self.stdout.write(f'Expired memories revoked: {count}')
