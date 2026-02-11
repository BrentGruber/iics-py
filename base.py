"""Shared constants, helpers, and error-raising logic"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from exceptions import (
    IICSError,
    IICSAuthError,
    IICSNotFoundError,
    IICSRateLimitError,
    IICSServerError,
    IICSValidationError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# -- Default IICS login URLs by region ----------------------------


class ApiVersion(str, Enum):
    """IICS API versions"""

    V2 = "v2"
    V3 = "v3"


DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_REAUTH_ATTEMPTS = 2
SESSION_EXPIRED_CODES = {401, 403}
API_V2_PREFIX = "/api/v2"
API_V3_PREFIX = "/api/v3"

SESSION_HEADER = {ApiVersion.V2: "icSessionId", ApiVersion.V3: "INFA-SESSION-ID"}

BASE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def build_request_headers(
    session_id: str,
    api_version: ApiVersion,
    *,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build the full set of request headers for a given API version.

    Merges base headers, version specific headers, the correct
    session auth header, and any caller supplied overrides
    """
    headers = {
        **BASE_HEADERS,
        SESSION_HEADER[api_version]: session_id,
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def raise_for_status(status_code: int, body: str, url: str) -> None:
    """Map HTTP status codes to typed IICS exceptions."""
    if 200 <= status_code < 300:
        return
    msg = f"HTTP {status_code} error for {url}: {body[:500]}"
    if status_code == 401:
        raise IICSAuthError(msg, status_code, body)
    if status_code == 403:
        raise IICSAuthError(msg, status_code, body)
    if status_code == 404:
        raise IICSNotFoundError(msg, status_code, body)
    if status_code == 429:
        raise IICSRateLimitError(msg, status_code, body)
    if status_code >= 500:
        raise IICSServerError(msg, status_code, body)
    raise IICSError(msg, status_code, body)


def parse_model(model_cls: type[T], data: Any) -> T:
    """Parse a dict into a pydantic model with a friendly error"""
    try:
        return model_cls.model_validate(data)
    except ValidationError as e:
        logger.error(f"Failed to parse {model_cls.__name__}: {e}")
        raise IICSValidationError(
            f"Failed to parse {model_cls.__name__}: {e}", None, str(data)
        ) from e


def parse_model_list(model_cls: type[T], data: Any) -> list[T]:
    """Parse a list of dicts into a list of pydantic models with a friendly error"""
    if not isinstance(data, list):
        raise IICSValidationError(
            f"Expected a list to parse into {model_cls.__name__} models, got {type(data)}",
            None,
            str(data),
        )
    return [parse_model(model_cls, item) for item in data]
