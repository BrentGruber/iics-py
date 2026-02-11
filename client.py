"""Asynchronous IICS REST API client using httpx.

Features:
    - Connection pooling with HTTP/2 support
    - Configurable concurrency limits
    - Native async context manager
    - Built in retry with exponential backoff

Usage:

    async with AsyncIICSClient(login_url="us", username="...", password="...") as client:
        connections = await client.list_connections()

        # Concurrent requests
        import asyncio
        conns, envs, agents = await asyncio.gather(
            client.list_connections(),
            client.list_environments(),
            client.list_agents()
        )
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from base import (
    ApiVersion,
    API_V2_PREFIX,
    API_V3_PREFIX,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_REAUTH_ATTEMPTS,
    SESSION_EXPIRED_CODES,
    build_request_headers,
    parse_model,
    parse_model_list,
    raise_for_status,
)
from exceptions import IICSAuthError
from models import (
    SessionInfo,
    Connection,
)

logger = logging.getLogger(__name__)


class AsyncIICSClient:
    """Asynchronous client for the IICS REST API

    Args:
        login_url (str): IICS login URL
        username (str): IICS username
        password (str): IICS password
        timeout (float, optional): Request timeout in seconds. Defaults to 30.
        max_retries (int, optional): Maximum number of retries for failed requests. Defaults to 3.
        http2: Enable HTTP/2 support (required ``httpx[http2]``)
        max_connections: Maximum concurrent conncetions
        max_keepalive_connections: Maximum idle keep-alive connections
    """

    def __init__(
        self,
        login_url: str,
        username: str,
        password: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_reauth_attempts: int = DEFAULT_MAX_REAUTH_ATTEMPTS,
        http2: bool = True,
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
    ) -> None:
        self._login_url = login_url
        self._username = username
        self._password = password
        self._timeout = timeout
        self._max_retries = max_retries
        self._max_reauth_attempts = max_reauth_attempts
        self._http2 = http2
        self._session_info: SessionInfo | None = None

        # Configure transport with retry and connection pooling
        self._transport = httpx.AsyncHTTPTransport(
            retries=max_retries,
            http2=http2,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
        )
        self._client = httpx.AsyncClient(
            transport=self._transport,
            timeout=httpx.Timeout(timeout),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )

    # -- Async Context Manager ---------------------------------

    async def __aenter__(self) -> AsyncIICSClient:
        await self.login()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.logout()
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx client and release connections."""
        await self._client.aclose()

    # -- Properties -------------------------------------------

    @property
    def session_info(self) -> SessionInfo:
        if self._session_info is None:
            raise IICSAuthError("Not authenticated. Call login() first.")
        return self._session_info

    @property
    def base_url(self) -> str:
        return self.session_info.server_url.rstrip("/")

    @property
    def is_authenticated(self) -> bool:
        return self._session_info is not None

    # -- Internal HTTP ----------------------------------------

    def _url(self, path: str, *, prefix: str = API_V3_PREFIX) -> str:
        return f"{self.base_url}{prefix}{path}"

    def _headers(
        self,
        api_version: ApiVersion,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        return build_request_headers(
            self.session_info.session_id,
            api_version,
            extra_headers=extra_headers,
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        api_version: ApiVersion = ApiVersion.V3,
        json: Any = None,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        for attempt in range(1 + self._max_reauth_attempts):
            headers = self._headers(api_version, extra_headers)
            resp = await self._client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
            )
            body = resp.text

            # If session expired and we haven't exhausted reauth attempts, try to re-login and retry the request
            if (
                resp.status_code in SESSION_EXPIRED_CODES
                and attempt <= self._max_reauth_attempts
            ):
                logger.info(
                    "Session expired (HTTP %d). reauthenticating and retrying request (attempt %d/%d)...",
                    resp.status_code,
                    attempt + 1,
                    self._max_reauth_attempts,
                )
                try:
                    await self.login()
                except IICSAuthError:
                    # Re-login iteself failed - raise the origin auth error
                    raise_for_status(resp.status_code, body, url)
                continue

            raise_for_status(resp.status_code, body, url)
            if not body or resp.status_code == 204:
                return None
            return resp.json()

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        prefix: str = API_V3_PREFIX,
        api_version: ApiVersion = ApiVersion.V3,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        return await self._request(
            "GET",
            self._url(path, prefix=prefix),
            params=params,
            api_version=api_version,
            extra_headers=extra_headers,
        )

    async def _post(
        self,
        path: str,
        *,
        json: Any = None,
        prefix: str = API_V3_PREFIX,
        api_version: ApiVersion = ApiVersion.V3,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        return await self._request(
            "POST",
            self._url(path, prefix=prefix),
            json=json,
            api_version=api_version,
            extra_headers=extra_headers,
        )

    async def _put(
        self,
        path: str,
        *,
        json: Any = None,
        prefix: str = API_V3_PREFIX,
        api_version: ApiVersion = ApiVersion.V3,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        return await self._request(
            "PUT",
            self._url(path, prefix=prefix),
            json=json,
            api_version=api_version,
            extra_headers=extra_headers,
        )

    async def _delete(
        self,
        path: str,
        *,
        prefix: str = API_V3_PREFIX,
        api_version: ApiVersion = ApiVersion.V3,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        return await self._request(
            "DELETE",
            self._url(path, prefix=prefix),
            api_version=api_version,
            extra_headers=extra_headers,
        )

    # -- raw requests ---------------------------------------

    async def raw_get(self, path: str, **kwargs: Any) -> Any:
        """Make a raw GET request to the specified API path."""
        return await self._request("GET", f"{self.base_url}{path}", **kwargs)

    async def raw_post(self, path: str, **kwargs: Any) -> Any:
        """Make a raw POST request to the specified API path."""
        return await self._request("POST", f"{self.base_url}{path}", **kwargs)

    # -- Auth ----------------------------------------------

    async def login(self) -> SessionInfo:
        """Authenticate with IICS and store session information."""
        url = f"{self._login_url}/ma/api/v2/user/login"
        resp = await self._client.post(
            url,
            json={
                "@type": "login",
                "username": self._username,
                "password": self._password,
            },
        )
        raise_for_status(resp.status_code, resp.text, url)
        info = parse_model(SessionInfo, resp.json())
        self._session_info = info
        self._client.headers["icSessionId"] = info.session_id
        logger.info(
            "Logged in as %s (org=%s), server=%s",
            info.name,
            info.org_id,
            info.server_url,
        )
        return info

    async def logout(self) -> None:
        """End the current IICS session"""
        if self._session_info is None:
            return
        try:
            url = f"{self._login_url}/ma/api/v2/user/logout"
            await self._client.post(url)
            logger.info("Logged out.")
        except Exception as e:
            logger.warning("Logout failed: %s", e)
        finally:
            self._session_info = None
            self._client.headers.pop("icSessionId", None)

    async def list_connections(self) -> list[Connection]:
        response = await self._get("/connection", api_version=ApiVersion.V2)
        connections = response.get("connections", [])
        return parse_model_list(Connection, connections)
