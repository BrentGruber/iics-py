"""Custom exceptions for the IICS REST API client"""

from __future__ import annotations


class IICSError(Exception):
    """Base class for all IICS REST API exceptions"""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class IICSAuthError(IICSError):
    """Raised when authentication fails"""


class IICSNotFoundError(IICSError):
    """Raised when a requested resource is not found"""


class IICSRateLimitError(IICSError):
    """Raised when the API rate limit is exceeded"""


class IICSServerError(IICSError):
    """Raised when the server returns a 5xx error"""


class IICSValidationError(IICSError):
    """Raised when the API response cannot be parsed or validated"""
