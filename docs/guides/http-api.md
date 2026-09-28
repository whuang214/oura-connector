# Use the HTTP API

Complete [setup](setup.md) first. The API runs on your computer and uses the same saved Oura login and response structures as MCP.

## Start the server

```powershell
uv run --locked oura-connector serve
```

Default address: `http://127.0.0.1:8766`. Leave this process running while making requests. For a custom profile, use `uv run --locked oura-connector --config C:/path/to/config.toml serve`.

A liveness check requires no authentication:

```powershell
curl.exe http://127.0.0.1:8766/health
```

Expected: `{"status":"ok"}`. Use `curl` on platforms where that is its executable name. This only checks the local server; it does not test Oura access.

## Make an authenticated request

Every route except `/health` requires `Authorization: Bearer <http_token>`. Setup generates this **local API token** separately from your Oura OAuth tokens and stores it in protected `credentials.json`. Windows encrypts that file; copying its ciphertext does not produce a usable bearer token.

From a second terminal in the checkout:

```powershell
uv run --locked python examples/http-day.py 2026-09-27 --include sleep --include readiness
```

The [example client](../../examples/http-day.py) uses the connector's credential loader to read the saved token, then sends a loopback HTTP request. It does not print the token, follow redirects, or use proxy environment variables. It prints the requested data. It uses package internals as a checkout example; the supported integration contract is HTTP.

Options include `--format source` and `--config C:/path/to/config.toml`. Use the same profile as the server. The date is required; omit `--include` to use your configured day sections.

For another HTTP client, provide the local API token through that client's protected secret storage and send this request shape. The placeholder below is not a working token:

```http
GET /days/2026-09-27?include=sleep&include=readiness HTTP/1.1
Host: 127.0.0.1:8766
Authorization: Bearer <http_token>
```

Do not use your Oura client secret or OAuth access token as the local API bearer token. Do not publish headers or health responses.

## Endpoints

All endpoints use GET. Dates use `YYYY-MM-DD`; datetime bounds include an offset.

| Route | Parameters | Purpose |
| --- | --- | --- |
| `/health` | None | Process liveness; unauthenticated |
| `/status` | None | Local date/timezone and credential state; no live probe |
| `/resources` | Optional `resource` | Discover names, filters, fields, and units |
| `/days/{date}` | Optional repeated `include`, `format` | One day |
| `/days` | `start_date`, `end_date`; optional repeated `include`, `format` | 1–31 inclusive days |
| `/records/{resource}` | Resource-specific bounds; optional `cursor`, `page_budget`, `format` | Collection retrieval |
| `/records/{resource}/{record_id}` | Optional `format` | One supported source record |

`format` accepts `compact` or `source` (default: `compact`). Use `/resources?resource=sleep` to discover a collection's filters. Date collections take `start_date`/`end_date`; time-series collections take `start_datetime`/`end_datetime`; singleton/device resources may accept no bounds. When resuming, send `cursor` from `continuation`; the original bounds are carried in it.

For day sections, use repeated keys: `include=sleep&include=readiness`, not a comma-separated string. Default and optional sections are described in the [MCP guide](mcp.md#tools); both interfaces use the same section registry.

## Results and errors

Successful requests can contain per-source `partial`, `unavailable`, or `error` results. Inspect collection status and `complete`, even after HTTP 200. Shared semantics are in the [data reference](../reference/data.md).

| HTTP status | Meaning |
| --- | --- |
| 400 | Unrecognized Host header |
| 401 | Local bearer token missing or incorrect |
| 403 | Browser-origin request rejected |
| 413 | Response exceeds a configured limit |
| 422 | Invalid request arguments |
| 502 | Top-level upstream API failure |
| 503 | Top-level authentication/configuration/connector failure |
| 504 | Operation timed out |

The server is loopback-only. It rejects browser Origin headers and unknown Host values, disables CLI access logs, and marks application responses `no-store`. There is no public remote mode or Swagger UI. Receiving clients may still retain data. See [troubleshooting](troubleshooting.md) for diagnosis.
