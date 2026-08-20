"""Exceptions raised by the Xarkeo client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class XarkeoError(Exception):
    """Base class for all Xarkeo SDK errors."""


class ConfigurationError(XarkeoError):
    """Raised when the client is missing required configuration."""


class TransportError(XarkeoError):
    """Raised when a request cannot reach the API."""


class ApiError(XarkeoError):
    """Raised for an API response with a non-success HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response_data: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
        self.headers = dict(headers or {})


class AuthenticationError(ApiError):
    """Raised when the supplied API token is absent, invalid, or unauthorized."""


class NotFoundError(ApiError):
    """Raised when the requested API resource does not exist."""


class PaginationError(XarkeoError):
    """Raised when an API page response breaks its expected pagination contract."""


class ValidationError(ApiError):
    """Raised when the API rejects a request as invalid."""


class RateLimitError(ApiError):
    """Raised when the API rate limit is exceeded."""

    def __init__(self, *args: Any, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after
