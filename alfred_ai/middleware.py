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
