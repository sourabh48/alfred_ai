"""Signed-in local diagnostics; inference runs only after an explicit CSRF-protected POST."""
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .services.local_diagnostics import benchmark_local_ai
from .services.native_readiness import native_readiness_snapshot


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def diagnostics_view(request):
    snapshot = native_readiness_snapshot()
    checks = [dict(item, state='running' if item['ready'] else 'requires_user_action') for item in snapshot['checks']]
    try:
        executor = MigrationExecutor(connection)
        pending = len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
        checks.append(dict(label='Database schema', state='requires_user_action' if pending else 'running',
                           detail=f'{pending} pending migration(s).' if pending else 'The selected database matches this source.',
                           manual_task='Review migrations and make a private backup before approving an upgrade.' if pending else ''))
    except Exception:
        checks.append(dict(label='Database schema', state='error', detail='Schema inspection failed.',
                           manual_task='Keep the existing data folder and backups. Check the local server log.'))
    for item in checks:
        item['state_label'] = item['state'].replace('_', ' ').capitalize()
    error = ''
    results = None
    if request.method == 'POST':
        try:
            acquired = cache.add('native:diagnostics:inference', True, timeout=60)
        except Exception:
            acquired = False
        if acquired:
            results = benchmark_local_ai()
        else:
            error = 'A local inference test was recently started, or the cache is unavailable. Wait one minute and retry.'
    response = render(request, 'settings/diagnostics.html', {
        'checks': checks, 'inference': results, 'diagnostic_error': error,
        'chat_model': settings.ALFRED_MEMORY_OLLAMA_MODEL,
        'database_path': str(Path(connection.settings_dict['NAME']).resolve()) if request.user.is_superuser else '',
        'native_runtime': getattr(settings, 'ALFRED_NATIVE_RUNTIME', False),
    })
    return response
