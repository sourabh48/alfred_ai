"""Fill one person's brain with a Gemini practice set for the travel reader, using their own saved Gemini key."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ml_engine.services.brain_practice import generate
from apps.ml_engine.services.memory_reasoning import forget_openai, saved_key
from apps.ml_engine.services.persistent_memory import MemoryStore


class Command(BaseCommand):
    help = "Ask Gemini for made-up trip messages and keep the ones the travel reader's checks accept (owner choice 2026-11-20)."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Username whose brain receives the examples.")
        parser.add_argument("--count", type=int, default=500)

    def handle(self, **options):
        if not 1 <= options["count"] <= 1000:
            raise CommandError("Choose between 1 and 1000 examples.")
        user = get_user_model().objects.filter(username=options["user"], is_active=True).first()
        if user is None:
            raise CommandError("No such active user.")
        key = saved_key(forget_openai(MemoryStore(settings.ALFRED_MEMORY_DIR), user))
        if not key:
            raise CommandError("Save a Gemini key in Settings first.")
        result = generate(user, options["count"], key=key)
        self.stdout.write(f"Kept {result['kept']} of {result['asked']} examples ({result['rejected']} failed the reader's "
                          f"checks)." + (f" Stopped early: {result['stopped']}." if result["stopped"] else ""))
