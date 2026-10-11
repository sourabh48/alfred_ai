"""Account deletion must revoke local memory independently of family membership."""
from pathlib import Path
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver


@receiver(pre_delete, sender=settings.AUTH_USER_MODEL)
def revoke_deleted_owner(sender, instance, **kwargs):
    if (Path(settings.ALFRED_MEMORY_DIR) / 'verified.sqlite3').exists():
        from .services.persistent_memory import MemoryStore
        MemoryStore(settings.ALFRED_MEMORY_DIR).reset_owner(instance)
