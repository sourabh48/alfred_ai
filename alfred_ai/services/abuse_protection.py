"""Local/LAN login and API quotas; authentication and CSRF remain independent."""
from hashlib import sha256
import hmac
from math import ceil
import re
import unicodedata

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from .api_errors import safe_error_details
from .throttling import reserve_attempts


EXPENSIVE_PATH = re.compile(r'/(?:import-pdf|import-statement|upload|upload-report|retry|refresh|research|discover|train|analyze|generate|job-match|recruiter-match|explain|personal-insights|runtime-control)(?:/|$)|/payoff/$|/bike-services/import/$')


def _identity(value):
    return hmac.new(settings.SECRET_KEY.encode(), str(value).encode('utf-8'), sha256).hexdigest()


class AbuseProtectionMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path_info
        login = request.method == 'POST' and path in ('/', '/login/', '/admin/login/')
        signup = request.method == 'POST' and path == '/signup/'
        authenticated = request.user.is_authenticated
        if path == '/' and authenticated:
            login = False
        api = authenticated and path.startswith('/api/')
        if not (login or signup or api):
            return None
        buckets = []
        def budget(scope, identity, setting):
            buckets.append(((scope, identity), getattr(settings, f'ALFRED_{setting}_LIMIT'),
                getattr(settings, f'ALFRED_{setting}_WINDOW_SECONDS')))
        try:
            if login or signup:
                ip = _identity(request.META.get('REMOTE_ADDR', ''))
                operation = 'LOGIN' if login else 'SIGNUP'
                budget(operation + '-ip', ip, operation + '_IP')
                budget(operation + '-global', 'all', operation + '_GLOBAL')
                if login:
                    username = unicodedata.normalize('NFKC', request.POST.get('username', '')[:254]).casefold()
                    budget('LOGIN-account', _identity(username), 'LOGIN_ACCOUNT')
            if api:
                account = _identity(f'{request.user.pk}:{request.user.date_joined.isoformat()}')
                budget('API-account', account, 'API_ACCOUNT')
                budget('API-global', 'all', 'API_GLOBAL')
                document_search = request.method == 'POST' and re.fullmatch(r'/api/ai/financial-documents/(?:expense|loan|investment)/[0-9]+/search/', path)
                if (request.content_type == 'multipart/form-data' and request.FILES) or EXPENSIVE_PATH.search(path) or document_search or path.startswith('/api/ai/document-corpus/') or (path.startswith('/api/ai/memories/') and request.method == 'POST'):
                    budget('EXPENSIVE-account', account, 'EXPENSIVE_ACCOUNT')
                    budget('EXPENSIVE-global', 'all', 'EXPENSIVE_GLOBAL')
            retry = reserve_attempts(settings.ALFRED_ABUSE_THROTTLE_DIR, buckets)
        except Exception as exc:
            message = 'Request protection is temporarily unavailable. Please try again.'
            error = safe_error_details(exc, message, logger_name=__name__)
            response = JsonResponse(error, status=503) if api else self._auth_response(request, f"{message} Reference: {error['error_id']}.", 503)
            response['Cache-Control'] = 'no-store'
            return response
        if retry:
            message = 'Too many requests. Please wait and try again.'
            response = JsonResponse({'detail': message}, status=429) if api else self._auth_response(request, message, 429)
            response['Retry-After'] = str(max(1, ceil(retry)))
            response['Cache-Control'] = 'no-store'
            return response
        return None

    @staticmethod
    def _auth_response(request, message, status):
        from django.contrib.auth.forms import AuthenticationForm
        if request.path_info == '/signup/':
            from apps.users.forms import AlfredSignUpForm
            return render(request, 'registration/signup.html', {'form': AlfredSignUpForm(),
                'protection_message': message, 'hide_sidebar': True, 'hide_nav_auth_actions': True}, status=status)
        return render(request, 'registration/login.html', {'form': AuthenticationForm(request),
            'protection_message': message, 'hide_sidebar': True, 'hide_nav_auth_actions': True}, status=status)
