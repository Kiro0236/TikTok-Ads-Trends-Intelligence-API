"""
Custom exception hierarchy for the API.

Every exception maps to a stable error `code` and an HTTP status,
so the exception handlers can produce a consistent JSON error body:

    {
        "error": {
            "code": "AD_NOT_FOUND",
            "message": "...",
            "details": {...}
        }
    }
"""
from typing import Any


class AppError(Exception):
    """Base class for all application-level errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.message = message or self.message
        self.details = details or {}
        super().__init__(self.message)


class InvalidParametersError(AppError):
    code = "INVALID_PARAMETERS"
    status_code = 422
    message = "One or more request parameters are invalid."


class AdNotFoundError(AppError):
    code = "AD_NOT_FOUND"
    status_code = 404
    message = "The requested advertisement could not be found."


class ProviderUnavailableError(AppError):
    """Raised when the upstream data provider cannot be reached or fails."""

    code = "PROVIDER_UNAVAILABLE"
    status_code = 502
    message = "The upstream data provider is currently unavailable."


class ProviderRateLimitedError(AppError):
    code = "PROVIDER_RATE_LIMITED"
    status_code = 429
    message = "The upstream data provider rate limit has been exceeded."


class ProviderParsingError(AppError):
    code = "PROVIDER_PARSING_ERROR"
    status_code = 502
    message = "Failed to parse the response received from the data provider."


class CacheError(AppError):
    """Raised when Redis is unreachable or a cache operation fails.

    Cache failures should never break the request — services must catch
    this and fall back to a live fetch. It is defined here so that any
    layer that wants to surface it explicitly can do so consistently.
    """

    code = "CACHE_ERROR"
    status_code = 500
    message = "A caching backend error occurred."


class RateLimitExceededError(AppError):
    """Raised by API-level rate limiting (per API key), not provider-side."""

    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    message = "You have exceeded the allowed number of requests. Please slow down."
