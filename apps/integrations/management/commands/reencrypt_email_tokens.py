import json

from django.core.management.base import BaseCommand, CommandError

from apps.integrations.services.token_rotation import reencrypt_email_tokens


class Command(BaseCommand):
    help = 'Verify email OAuth token readability; --apply atomically re-encrypts under the primary key.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        try:
            report = reencrypt_email_tokens(apply=options['apply'])
        except Exception:
            raise CommandError('Token rotation failed; transaction rolled back. Keep all keys and the recovery backup.') from None
        self.stdout.write(json.dumps(dict(mode='apply' if options['apply'] else 'dry-run', **report), sort_keys=True))
        if report['invalid']:
            raise CommandError('Unreadable tokens remain. Keep all keys and the recovery backup; do not retire a fallback.')
