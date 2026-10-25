"""Send one fixed synthetic prompt; never load financial records or saved memory."""
import json
from django.core.management.base import BaseCommand
from apps.ml_engine.core.alfred_router import alfred_router


class Command(BaseCommand):
    help = 'Test opt-in development Gemini connectivity with a fixed nonpersonal prompt.'
    requires_system_checks = []

    def handle(self, **options):
        self.stdout.write(json.dumps(alfred_router.route('gemini-development-smoke', {})))
