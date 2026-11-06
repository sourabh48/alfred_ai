"""Native runtime health and private upload downloads."""
import os
import time
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.core.cache import cache
from django.db import connection

from alfred_ai.services.upload_privacy import PRIVATE_FILE_FIELDS


def native_health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        heartbeat = cache.get("native:worker-heartbeat", {})
        ready = (
            heartbeat.get("instance") == os.environ.get("ALFRED_NATIVE_INSTANCE")
            and time.time() - heartbeat.get("time", 0) < 15
        )
    except Exception:
        ready = False
    response = JsonResponse({
        "status": "ok" if ready else "starting",
        "instance": os.environ.get("ALFRED_NATIVE_INSTANCE", ""),
    }, status=200 if ready else 503)
    response["Cache-Control"] = "no-store"
    return response


@login_required
def private_media(request, path):
    root = Path(settings.MEDIA_ROOT).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise Http404
    name = target.relative_to(root).as_posix()
    for model, field, owner in PRIVATE_FILE_FIELDS:
        if apps.get_model(model).objects.filter(**{field: name, owner: request.user.pk}).exists():
            try:
                source = target.open("rb")
            except OSError:
                raise Http404 from None
            response = FileResponse(source, as_attachment=True, filename=target.name)
            response["Cache-Control"] = "private, no-store"
            return response
    raise Http404
