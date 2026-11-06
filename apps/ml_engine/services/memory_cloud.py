"""Provider-neutral encrypted sync dispatch: the local mock or Cloudflare R2. AWS stays decommissioned."""
import time
from django.conf import settings
from .memory_r2 import R2MemoryProvider, configured_profile
from .memory_sync import MemorySynchronizer, MockCloudProvider, SyncUnavailable, remaining
from .persistent_memory import _owner


def configured_provider():
    requested = settings.ALFRED_MEMORY_SYNC_PROVIDER
    if requested == 'r2':  # needs the owner's activation flag and a complete, valid R2 profile
        return 'r2' if settings.ALFRED_MEMORY_CLOUD_AUTHORIZED and configured_profile() else ''
    if requested and requested != 'mock':
        return ''
    return 'mock' if settings.ALFRED_MEMORY_SYNC_MOCK_DIR else ''


def synchronizer(store, user, *, deadline=None):
    deadline = deadline or time.monotonic() + 5
    kind = configured_provider()
    if kind == 'r2':
        return MemorySynchronizer(store, R2MemoryProvider(_owner(user), configured_profile()))
    if kind != 'mock':
        raise SyncUnavailable('No approved non-AWS cloud synchronization provider is configured.')
    provider = MockCloudProvider(settings.ALFRED_MEMORY_SYNC_MOCK_DIR, timeout=remaining(deadline))
    return MemorySynchronizer(store, provider)
