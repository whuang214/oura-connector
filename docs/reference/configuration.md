# Configuration

Edit the non-secret `config.toml` created during [setup](../guides/setup.md#local-files). Restart running MCP/HTTP processes after changes. An [example TOML](../../examples/config.toml) shows common settings; copy only the settings you want to change.

The default profile directory is documented in [setup](../guides/setup.md#local-files). For another profile:

```powershell
uv run --locked oura-connector --config C:/path/to/config.toml doctor
```

The filename must end in `.toml` and must not start with `.env`. Unknown keys are rejected. Keep secrets out of TOML: `client_secret`, `access_token`, `http_token`, `token_file`, `authorize_url`, and `token_url` are not accepted there.

## Account and output

| Setting | Default | Meaning |
| --- | --- | --- |
| `client_id` | Not set | Your Oura developer app ID; set through setup/UI |
| `redirect_uri` | `http://localhost:8765/callback` | Must match Oura's registered URI exactly |
| `timezone` | `UTC` | IANA timezone for local date/status; choose your own during setup |
| `default_sections` | `sleep`, `readiness`, `activity`, `stress`, `spo2` | Day sections when a request omits `include` |
| `scopes` | `daily`, `heartrate`, `workout`, `tag`, `session`, `spo2`, `personal`, `email` | Requested OAuth permissions; reauthorize after changing |
| `compact_fields` | Resource defaults | Optional source-field selections by resource |

`default_sections` must be nonempty and unique. Valid names are in the [MCP tool reference](../guides/mcp.md#tools). Changing timezone does not reassign source Oura days or convert timestamps; see [data semantics](data.md).

For example, request only sleep and readiness by default:

```toml
default_sections = ["sleep", "readiness"]
```

To limit authorization to daily summaries, choose that permission in the portal and set `scopes = ["daily"]` before signing in again. Other collections may become unavailable. Changing `scopes` does not change an already-issued grant until reauthorization.

## Compact fields

Choose fields by their **source names**, not the connector's readable labels:

```toml
[compact_fields]
sleep = ["total_sleep_duration", "time_in_bed", "average_hrv", "average_heart_rate"]
```

This replaces the default selection for that resource. IDs, source day/type, and timestamps remain. Use `oura_resources` or `/resources` to discover default fields and units. `format="source"` bypasses field selection. Selection does not evaluate expressions or calculate custom scores.

## Limits

| Setting | Default | Allowed range |
| --- | --- | --- |
| `max_pages` | 10 | 1–100 |
| `max_records` | 2,000 | 1–100,000 |
| `max_page_bytes` | 4,000,000 | 1,024–50,000,000 |
| `max_response_bytes` | 8,000,000 | 1,024–100,000,000 |
| `concurrency` | 3 | 1–10 |
| `timeout_seconds` | 20 | Greater than 0, at most 120 |
| `operation_timeout_seconds` | 90 | Greater than 0, at most 600 |
| `max_retries` | 2 | 0–5 |
| `token_refresh_skew_seconds` | 60 | 0–600 |

Pages and records limit a collection retrieval. `max_page_bytes` bounds one upstream response; `max_response_bytes` bounds a final connector response. `concurrency` bounds source fanout for day requests. `timeout_seconds` configures HTTP request timeouts; `operation_timeout_seconds` bounds a collection operation. The refresh skew renews credentials before their expiry.

Query date/time span limits are separate and documented in [data](data.md#dates-and-limits). Lower `page_budget` on a collection request to fetch fewer upstream pages in that call. Truncation exposes status/continuation or an error; JSON is not silently cut off.

## HTTP listener

| Setting | Default | Allowed values |
| --- | --- | --- |
| `http_host` | `127.0.0.1` | `127.0.0.1`, `localhost`, `::1` |
| `http_port` | 8766 | 1024–65535 |

The server remains loopback-only and bearer-authenticated. For IPv6 URLs, put brackets around the host: `http://[::1]:8766`. The HTTP port and OAuth callback port are different services; changing one does not change the other.

## Editing behavior

Desktop settings preserve supported advanced TOML values but rewrite the file without preserving comments. Do not change settings while another setup/save operation is running. Use the same profile in login, MCP, and HTTP processes; see [troubleshooting](../guides/troubleshooting.md#alternate-profiles).
