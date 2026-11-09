from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .services.data_sources import data_sources_snapshot


@login_required
@never_cache
@require_GET
def data_sources_view(request):
    return render(request, 'data_sources.html', data_sources_snapshot(request.user))
