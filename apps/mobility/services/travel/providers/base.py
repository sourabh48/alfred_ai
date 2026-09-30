from dataclasses import asdict, dataclass, field
from datetime import timedelta
import json
import math

from alfred_ai.services.public_http import PublicHTTPError, request


FRESHNESS = {"LIVE", "RECENTLY_VERIFIED", "CACHED", "ESTIMATED", "USER_PROVIDED", "STATIC_REFERENCE", "UNKNOWN"}


class ProviderError(Exception):
    """Only stable, non-secret codes cross the provider boundary."""

    def __init__(self, code, *, retry_after=60):
        self.code = code
        self.retry_after = min(max(int(retry_after), 1), 86400)
        super().__init__(code)


@dataclass
class ProviderResult:
    provider: str
    category: str
    success: bool = False
    status: str = "unavailable"
    freshness: str = "UNKNOWN"
    confidence: str = "UNKNOWN"
    payload: dict = field(default_factory=dict)
    source_url: str = ""
    attribution: str = ""
    retrieved_at: str | None = None
    verified_at: str | None = None
    expires_at: str | None = None
    response_hash: str = ""
    request_parameters: dict = field(default_factory=dict)
    error: str = ""
    stale: bool = False
    cached: bool = False
    fallback: list = field(default_factory=list)

    def as_dict(self):
        return asdict(self)


class Provider:
    name = "unconfigured"
    category = "unknown"
    source_url = ""
    attribution = ""
    ttl = timedelta(hours=1)
    # Conservative application budgets, not a promise of a provider's free quota.
    limits = {"minute": 10, "hour": 100, "day": 500, "month": 5000}
    min_interval = 1
    allowed_parameters = frozenset()
    version = 1
    cache_partition = "public"

    def unavailable_reason(self):
        return "provider_not_configured"

    def parameters(self, parameters):
        clean = {k: v for k, v in parameters.items() if k in self.allowed_parameters}
        # Reject non-JSON values, NaN and excessively large requests before storage.
        if len(json.dumps(clean, allow_nan=False)) > 4000:
            raise ProviderError("invalid_parameters")
        return clean

    def fetch(self, parameters):
        raise ProviderError("provider_not_configured")

    def normalize(self, raw, parameters):
        raise NotImplementedError

    def cache_ttl(self, parameters):
        return self.ttl

    def expires_at(self, payload, parameters, retrieved):
        return retrieved+self.cache_ttl(parameters)


def number(value, *, low=None, high=None):
    if isinstance(value, bool):
        raise ValueError("Not a number")
    value = float(value)
    if not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError("Out of bounds")
    return value


def request_json(method, url, **kwargs):
    """All travel HTTP goes through the shared, pinned public HTTPS boundary."""
    if "json" in kwargs:
        kwargs["json_body"] = kwargs.pop("json")
    try:
        response = request(method, url, **kwargs)
        return response.json(), response.response_hash
    except PublicHTTPError as exc:
        raise ProviderError(exc.code, retry_after=exc.retry_after) from None
