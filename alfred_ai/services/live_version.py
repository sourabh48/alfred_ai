"""Per-user data version: open pages refetch only after it changes, never on a timer."""
from contextvars import ContextVar
from hashlib import sha256
from uuid import uuid4

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save

request_method = ContextVar("alfred_request_method", default=None)
# Page loads may write logs or evidence rows; counting those would make an open page reload itself forever.
READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# Linked accounts see only these scoped tokens, never the full one, so a link does not reveal
# when the other person is online or edits private records.
SHARED_SCOPE_BY_APP = {
    "family": "dependents",
    "expenses": "financial",
    "loans": "financial",
    "investments": "financial",
    "budgets": "financial",
    # Vehicle, credit and career records also feed the shared financial baseline.
    "mobility": "financial",
    "integrations": "financial",
    "career": "financial",
}
# Diagnostics, not owner data: a failing panel logs on every reload and would otherwise reload every open tab.
IGNORED_MODELS = frozenset({"reports.OperationalLog"})


def _key(user_id, scope="all"):
    return f"alfred:data-version:{user_id}:{scope}"


def bump_data_version(user_id, *scopes):
    cache.set_many({_key(user_id, scope): uuid4().hex for scope in ("all", *scopes)}, timeout=None)


def data_version(user):
    """One token for the owner plus the shared parts of every account whose data this owner's pages show."""
    from apps.family.services import family_context_user_ids, family_financial_user_ids

    keys = [_key(user.id)]
    keys += [_key(user_id, "dependents") for user_id in family_context_user_ids(user) if user_id != user.id]
    keys += [_key(user_id, "financial") for user_id in family_financial_user_ids(user) if user_id != user.id]
    tokens = cache.get_many(keys)
    return sha256("|".join(f"{key}={tokens.get(key, '')}" for key in keys).encode()).hexdigest()[:16]


def _owner_changed(sender, instance, **kwargs):
    if request_method.get() in READ_METHODS or sender._meta.label in IGNORED_MODELS:
        return
    user_id = getattr(instance, "user_id", None)
    if isinstance(user_id, int):
        # Cached summaries key on row counts and dates, which miss in-place edits; a new generation bypasses them.
        cache.set(f"alfred:materialized-generation:{user_id}", uuid4().hex, timeout=None)
        scope = SHARED_SCOPE_BY_APP.get(sender._meta.app_label)
        bump_data_version(user_id, *([scope] if scope else []))


def connect():
    # Covers background imports and jobs, and other owners' rows changed by a request.
    post_save.connect(_owner_changed, dispatch_uid="alfred-data-version-save")
    post_delete.connect(_owner_changed, dispatch_uid="alfred-data-version-delete")
