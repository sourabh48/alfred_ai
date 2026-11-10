from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .services.data_sources import data_sources_snapshot, knowledge_sources_snapshot


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def data_sources_view(request):
    context = data_sources_snapshot(request.user)
    if request.method == 'POST':
        if (request.GET or set(request.POST) - {'csrfmiddlewaretoken', 'action'} or
                request.POST.getlist('action') != ['check_knowledge']):
            return HttpResponseBadRequest('Choose the local knowledge readiness check.')
        context['knowledge'] = knowledge_sources_snapshot(request.user)
    return render(request, 'data_sources.html', context)
