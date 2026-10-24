"""Provider-neutral encrypted sync dispatch; AWS runtime integration is decommissioned."""
import time
from django.conf import settings
from .memory_sync import MemorySynchronizer, MockCloudProvider, SyncUnavailable, remaining


def configured_provider():
    requested = settings.ALFRED_MEMORY_SYNC_PROVIDER
    if requested and requested != 'mock':
        return ''
    return 'mock' if settings.ALFRED_MEMORY_SYNC_MOCK_DIR else ''


def synchronizer(store, user, *, deadline=None):
    deadline = deadline or time.monotonic() + 5
    if configured_provider() != 'mock':
        raise SyncUnavailable('No approved non-AWS cloud synchronization provider is configured.')
    provider = MockCloudProvider(settings.ALFRED_MEMORY_SYNC_MOCK_DIR, timeout=remaining(deadline))
    return MemorySynchronizer(store, provider)
