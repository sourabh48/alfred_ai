from django.db import connection

from alfred_ai.services.materialized_cache import invalidate_user_materialized_payloads

WRITE_SQL = ("INSERT", "UPDATE", "DELETE", "REPLACE")
# Session saves (pings, logins) and diagnostic logs are not owner data.
NOT_DATA_TABLES = ("django_session", "reports_operationallog")


class UserDataCacheMiddleware:
    """Refresh derived views after successful user API writes, including edits.

    Count/date revisions alone do not detect category or balance corrections.
    Django completes view transactions before returning through middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from alfred_ai.services.live_version import READ_METHODS, bump_data_version, request_method

        wrote = []

        def watch_writes(execute, sql, params, many, context):
            # Bulk .update() calls fire no model signals, so watch the SQL itself.
            if sql.lstrip()[:7].upper().startswith(WRITE_SQL) and not any(table in sql for table in NOT_DATA_TABLES):
                wrote.append(True)
            return execute(sql, params, many, context)

        token = request_method.set(request.method)
        try:
            if request.method in READ_METHODS:
                response = self.get_response(request)
            else:
                with connection.execute_wrapper(watch_writes):
                    response = self.get_response(request)
        finally:
            request_method.reset(token)
        user = getattr(request, "user", None)
        if (request.method in {"POST", "PUT", "PATCH", "DELETE"}
                and request.path.startswith("/api/")
                and 200 <= response.status_code < 300
                and user and user.is_authenticated):
            from apps.family.services import family_context_user_ids, family_financial_viewer_ids

            user_ids = set(family_context_user_ids(user)) | set(family_financial_viewer_ids(user))
            for user_id in user_ids:
                invalidate_user_materialized_payloads(user_id, reason="user_api_write")
            if wrote:
                bump_data_version(user.id)
        return response


class PersonalKeysMiddleware:
    """Each page uses the signed-in person's own keys for paid or limited services (owner decision 2026-11-19)."""

    def __init__(self, get_response):
        from django.core.signals import request_finished
        from alfred_ai.services import personal_keys
        self.get_response = get_response
        # Cleared once the response is fully sent (after any streaming), so the person never carries over on this thread.
        request_finished.connect(personal_keys.forget, dispatch_uid="alfred-personal-keys-forget")

    def __call__(self, request):
        from alfred_ai.services import personal_keys
        personal_keys.use_for(getattr(request, "user", None))
        return self.get_response(request)


class VerifiedSignInMiddleware:
    """Owner decision 2026-11-19: once Google, GitHub or Microsoft sign-in is set up, only people with an email one of
    them verified can use ALFRED, and this PC is reached as localhost, the address those providers send people back to."""

    OPEN = ("/login/", "/logout/", "/auth/", "/static/", "/favicon.ico", "/phone/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.auth import logout
        from django.http import JsonResponse
        from django.shortcuts import redirect
        from alfred_ai.services import social_login

        if not social_login.configured():
            return self.get_response(request)
        host, _, port = request.get_host().rpartition(":")
        if not host or not port.isdigit():  # no port given
            host, port = request.get_host(), ""
        if host in ("127.0.0.1", "[::1]") and request.method in ("GET", "HEAD"):
            # Google and Microsoft only return sign-ins to localhost, and a cookie set on one name is unknown to the other.
            return redirect(f"http://localhost{':' + port if port else ''}{request.get_full_path()}")
        user = request.user
        if user.is_authenticated and not request.path.startswith(self.OPEN) and not user.email_identities.exists():
            logout(request)
            if request.path.startswith("/api/"):
                return JsonResponse({"detail": "Sign in with Google, GitHub or Microsoft to continue."}, status=401)
            request.session["alfred_sign_in_error"] = "Sign in with Google, GitHub or Microsoft to continue. Passwords are no longer used."
            return redirect("login")
        return self.get_response(request)
