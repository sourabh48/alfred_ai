import json

from django.core.management.base import BaseCommand
from apps.mobility.services.travel.cache import cleanup_request_history


class Command(BaseCommand):
    help = 'Preview expired public Travel request telemetry; --apply deletes one bounded batch.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(cleanup_request_history(apply=options['apply']), sort_keys=True))
