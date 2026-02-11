# IICS REST API Client

A typed Python client for the **Informatica Intelligent Cloud Services (IICS)** REST API, with both synchronous (`requests`) and asynchronous (`httpx`) implementations sharing the same Pydantic v2 models and interface.

## Features

- **Sync + Async** — `IICSClient` (requests) and `AsyncIICSClient` (httpx) with identical method signatures
- **Pydantic v2 models** — typed responses with automatic `camelCase` → `snake_case` aliasing
- **API version–aware headers** — automatically sends `icSessionId` for v2 endpoints and `INFA-SESSION-ID` for v3 endpoints
- **Automatic session renewal** — transparently re-authenticates on 401/403 and retries the failed request
- **Context managers** — `with` (sync) and `async with` (async) handle login/logout lifecycle
- **Retry logic** — configurable retries with exponential backoff on 502/503/504
- **Custom exceptions** — `IICSAuthError`, `IICSNotFoundError`, `IICSRateLimitError`, `IICSServerError`
- **Connection pooling** — httpx transport with configurable pool limits
- **HTTP/2 support** — optional via `httpx[http2]`
- **Concurrent helpers** — `batch_start_jobs()` and `poll_job_status()` on the async client
- **Escape hatches** — `raw_get()` / `raw_post()` with explicit `api_version` for unwrapped endpoints

## Installation

```bash
pip install -e .

# Optional: HTTP/2 support
pip install -e ".[http2]"

# Development (pytest, respx, responses, ruff, mypy)
pip install -e ".[dev]"
```

**Requires Python 3.10+.**

## Quick Start

```python
from iics_py import AsyncIICSClient

async with AsyncIICSClient(
    login_url="us",             # or "em", "ap", or a full URL
    username="user@company.com",
    password="your-password",
) as client:

    # List connections (v2 endpoint — icSessionId header sent automatically)
    for conn in await client.list_connections():
        print(f"{conn.name} ({conn.type})")

    # Start a mapping task job (v2 endpoint)
    run = await client.start_job(task_id="abc123", task_type="MTT")
    print(f"Run ID: {run.run_id}")

    # Search objects (v3 endpoint — INFA-SESSION-ID header sent automatically)
    results = await client.search_objects(query="sales", object_type="MTT")
    for obj in results:
        print(f"{obj.name} ({obj.type})")
```

## API Version Handling

IICS exposes two API families with different path prefixes and authentication headers. The client handles this automatically per endpoint — you never need to set headers manually.

| Version | Path Prefix | Auth Header        | Endpoints                                                        |
|---------|-------------|--------------------|------------------------------------------------------------------|
| **v2**  | `/saas`     | `icSessionId`      | Connections, Runtime Envs, Agents, Jobs, Activity Log, Schedules, Audit Logs |
| **v3**  | `/api/v2`   | `INFA-SESSION-ID`  | Mapping Tasks, Taskflows, Object Search                          |

Each method in the client declares its API version internally. For example, `list_connections()` sends `icSessionId` while `list_mapping_tasks()` sends `INFA-SESSION-ID`.

For raw/escape-hatch calls, you can specify the version explicitly:

```python
from iics_client import ApiVersion

# v2 endpoint with icSessionId
data = await client.raw_get("/some/v2/path", api_version=ApiVersion.V2)

# v3 endpoint with INFA-SESSION-ID (default)
data = await client.raw_get("/some/v3/path", api_version=ApiVersion.V3)

# Override headers entirely
data = await client.raw_get("/custom", extra_headers={"X-Custom": "value"})
```

## Automatic Session Renewal

IICS sessions expire after a period of inactivity. Both clients detect 401/403 responses, re-authenticate transparently, and retry the original request with a fresh session — no manual intervention required.

```
Request → 401 Unauthorized
  └─ re-login() → new session ID
     └─ retry original request with new headers → 200 OK
```

The behavior is configurable:

```python
# Retry re-auth up to 3 times per request (default: 2)
client = AsyncIICSClient(login_url="us", username="...", password="...", max_reauth_attempts=3)

# Disable auto-renewal entirely
client = AsyncIICSClient(login_url="us", username="...", password="...", max_reauth_attempts=0)
```

If re-login itself fails (e.g. credentials were revoked), the original `IICSAuthError` is raised immediately — no infinite loops.

## Covered Endpoints

| Area                  | API | Methods                                              |
|-----------------------|-----|------------------------------------------------------|
| **Auth**              | v2  | `login()`, `logout()`                                |
| **Connections**       | v2  | `list`, `get`, `create`, `delete`                    |
| **Runtime Envs**      | v2  | `list`, `get`                                        |
| **Agents**            | v2  | `list`, `get`                                        |
| **Jobs**              | v2  | `start`, `stop`                                      |
| **Activity Log**      | v2  | `get` (filter by `task_id`, `run_id`)                |
| **Schedules**         | v2  | `list`, `get`                                        |
| **Audit Logs**        | v2  | `get` (filter by date range)                         |
| **Mapping Tasks**     | v3  | `list`, `get`                                        |
| **Taskflows**         | v3  | `list`, `get`                                        |
| **Object Search**     | v3  | `search` (by query, type, tag)                       |
| **Raw**               | any | `raw_get()`, `raw_post()` with explicit `api_version`|

## Async Features

| Feature               | Description                                                      |
|-----------------------|------------------------------------------------------------------|
| `batch_start_jobs()`  | Start multiple jobs concurrently via `asyncio.gather`            |
| `poll_job_status()`   | Poll activity log until a job hits SUCCESS/FAILED/STOPPED/WARNING|
| Connection pooling    | Configurable `max_connections` / `max_keepalive_connections`     |
| HTTP/2                | Optional via `http2=True` (requires `httpx[http2]`)              |

## Configuration

The Async Client accepts the following parameters:

| Param                       | Default | Description                                          |
|-----------------------------|---------|------------------------------------------------------|
| `login_url`                 | —       | `"us"`, `"em"`, `"ap"`, or full URL                 |
| `username`                  | —       | IICS username                                        |
| `password`                  | —       | IICS password                                        |
| `timeout`                   | `30`    | Per-request timeout (seconds)                        |
| `max_retries`               | `3`     | Retries on 502/503/504                               |
| `max_reauth_attempts`       | `2`     | Max re-login attempts on 401/403 per request         |
| `http2`                     | `False` | Enable HTTP/2                            |
| `max_connections`           | `20`    | Connection pool max size                 |
| `max_keepalive_connections` | `10`    | Max idle keep-alive connections          |

## Exception Hierarchy

All exceptions inherit from `IICSError` and carry `status_code` and `response_body` attributes:

```
IICSError
├── IICSAuthError          # 401, 403 (after reauth exhausted)
├── IICSNotFoundError      # 404
├── IICSRateLimitError     # 429
├── IICSServerError        # 5xx
└── IICSValidationError    # Pydantic parse failures
```

```python
from iics_client import IICSAuthError, IICSNotFoundError

try:
    conn = await client.get_connection("nonexistent-id")
except IICSNotFoundError as e:
    print(f"Not found (HTTP {e.status_code}): {e.response_body}")
except IICSAuthError as e:
    print(f"Auth failed after reauth attempts: {e}")
```

## Architecture

```
iics_client/
├── __init__.py          # Public exports (clients, models, exceptions, ApiVersion)
├── _base.py             # ApiVersion enum, header builders, shared error handling
├── models.py            # Pydantic v2 models (shared by both clients)
├── exceptions.py        # Typed exception hierarchy
├── client.py            # AsyncIICSClient — sync, requests
├── pyproject.toml
└── examples/
    ├__ basic_usage.py   # Sync example
```

Key design decisions:

- **`base.py`** centralizes all shared logic — URL resolution, API version constants, header building, HTTP-status-to-exception mapping, and Pydantic model parsing. Neither client duplicates this.
- **No global session headers** — auth headers are built per-request based on the target API version, so v2 and v3 calls within the same client never get the wrong header.
- **Login response routing** — the `serverUrl` from the IICS login response becomes the base URL for all subsequent API calls. This is how IICS routes you to your regional pod.

## Environment Variables

The example scripts expect:

```bash
export IICS_USERNAME="user@company.com"
export IICS_PASSWORD="your-password"
export IICS_LOGIN_URL="us"  # optional, defaults to "us"
```

## Testing

```bash
pip install -e ".[dev]"

# Run tests
pytest -v

# With coverage
pytest --cov=iics_client --cov-report=term-missing
```

Use `responses` to mock the sync client and `respx` to mock the async client:

```python
import responses
from iics_client import IICSClient

@responses.activate
def test_list_connections():
    responses.add(
        responses.POST,
        "https://dm-us.informaticacloud.com/ma/api/v2/user/login",
        json={
            "id": "user-1",
            "userName": "test@co.com",
            "orgId": "org-1",
            "serverUrl": "https://usw3.dm-us.informaticacloud.com",
            "icSessionId": "session-abc",
        },
    )
    responses.add(
        responses.GET,
        "https://usw3.dm-us.informaticacloud.com/saas/connection",
        json=[{"id": "c1", "orgId": "org-1", "name": "MyConn", "type": "ODBC"}],
    )

    with IICSClient(login_url="us", username="test@co.com", password="pass") as client:
        conns = client.list_connections()
        assert len(conns) == 1
        assert conns[0].name == "MyConn"
```

