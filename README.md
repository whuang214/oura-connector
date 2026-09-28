# Oura Connector

**Fetch your Oura data through MCP or a local HTTP API.**

Retrieve sleep, readiness, activity, and other available records by day, date range, or record ID. Runs on your computer using your own Oura developer application.

[Get started](docs/guides/setup.md) · [MCP guide](docs/guides/mcp.md) · [HTTP API guide](docs/guides/http-api.md) · [All documentation](docs/README.md)

## What you can fetch

| Request | Example |
| --- | --- |
| A day | Sleep and readiness for September 27 |
| A date range | Daily records for the last seven days |
| A collection | Workouts, heart rate, tags, or other available data |
| A record | One sleep period or workout by its Oura ID |

Choose readable `compact` output or `source` output with the original fields. Scores come from Oura; sleep periods stay separate. Responses report missing data and incomplete retrievals. Availability depends on your account and granted permissions.

## Quick start

Requires **Python 3.11+**, [uv](https://docs.astral.sh/uv/getting-started/installation/), and an Oura account with API access. Verified on Windows x64 with Python 3.12; other platforms are not yet verified.

```powershell
git clone https://github.com/whuang214/oura-connector.git
cd oura-connector
uv sync --locked
uv run --locked oura-connector ui
```

On Windows, after installation, double-click **[Open Oura.cmd](Open%20Oura.cmd)** in the repository folder to open Oura Connect. Reopen it anytime to see your saved sign-in or manage the connection. A desktop shortcut is optional.

1. Create your own app in the [Oura developer portal](https://developer.ouraring.com/applications). The [setup guide](docs/guides/setup.md#create-your-developer-app) explains every field.
2. Register `http://localhost:8765/callback`, enter your app's client ID and secret in Oura Connect, and approve access in your browser.
3. Choose MCP or HTTP below. They use the same saved sign-in.

Your Oura password stays on Oura's website. Credentials are stored locally; each user creates their own developer app. Prefer a terminal? Use the [CLI login instructions](docs/guides/setup.md#terminal-login).

## Use MCP

Add this to a client that supports local stdio MCP servers. Replace the checkout path with your own:

```json
{
  "mcpServers": {
    "oura": {
      "command": "uv",
      "args": ["run", "--locked", "--directory", "C:/path/to/oura-connector", "oura-connector", "mcp"]
    }
  }
}
```

For example, ask your client to fetch sleep and readiness for `2026-09-27`. The `oura_get_day` tool accepts:

```json
{"date": "2026-09-27", "include": ["sleep", "readiness"]}
```

[Tool reference and more examples](docs/guides/mcp.md)

## Use the HTTP API

Start the local server:

```powershell
uv run --locked oura-connector serve
```

In a second terminal, from the checkout:

```powershell
uv run --locked python examples/http-day.py 2026-09-27 --include sleep --include readiness
```

This sends `GET /days/2026-09-27?include=sleep&include=readiness` to the configured loopback server. The example loads your local bearer token without printing it. It prints returned records, which may contain personal data.

[Authentication, endpoints, and request examples](docs/guides/http-api.md)

## Readable results

A synthetic compact sleep-record excerpt:

```json
{
  "id": "example-sleep",
  "day": "2026-09-27",
  "type": "long_sleep",
  "total_sleep_seconds": 27000,
  "total_sleep_display": "7h 30m",
  "units": {"total_sleep_seconds": "seconds"}
}
```

The full response also includes retrieval status and completeness. [Understand dates, sleep, and output formats](docs/reference/data.md).

## Documentation

| I want to… | Read |
| --- | --- |
| Install and connect my account | [Setup](docs/guides/setup.md) |
| Connect an MCP client | [MCP](docs/guides/mcp.md) |
| Call endpoints from a script | [HTTP API](docs/guides/http-api.md) |
| Change fields, timezone, or limits | [Configuration](docs/reference/configuration.md) |
| Fix a connection or missing result | [Troubleshooting](docs/guides/troubleshooting.md) |
| Understand or contribute code | [Contributing](CONTRIBUTING.md) · [Architecture](docs/development/architecture.md) |

## Project information

Independent community software, provided under the [MIT license](LICENSE). Each person operates their own copy. [Privacy Policy](PRIVACY.md) · [Terms of Service](TERMS.md).
