from alfred_ai.services.materialized_cache import invalidate_user_materialized_payloads


class UserDataCacheMiddleware:
    """Refresh derived views after successful user API writes, including edits.

    Count/date revisions alone do not detect category or balance corrections.
    Django completes view transactions before returning through middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if (request.method in {"POST", "PUT", "PATCH", "DELETE"}
                and request.path.startswith("/api/")
                and 200 <= response.status_code < 300
                and user and user.is_authenticated):
            from apps.family.services import family_context_user_ids, family_financial_user_ids

            user_ids = set(family_context_user_ids(user)) | set(family_financial_user_ids(user))
            for user_id in user_ids:
                invalidate_user_materialized_payloads(user_id, reason="user_api_write")
        return response
