# Use MCP

Complete [setup](setup.md) first. The connector provides six read-only tools over **stdio**. Your MCP client launches the process; an HTTP server is not required.

## Connect a client

Use your client's supported local MCP configuration. This example is also available as [mcp.json](../../examples/mcp.json):

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

Replace the directory with your checkout. On macOS/Linux, use a path such as `/home/you/oura-connector`. If the client cannot find uv, use its absolute executable path. Clients have different configuration locations; this is a generic configuration example, not a client-specific installation command.

For a custom profile, add `"--config", "C:/path/to/config.toml"` immediately before `"mcp"`. Use the same profile you signed in with. Restart the MCP process after settings change. Never put client secrets or tokens in this JSON.

## Tools

| Tool | Required arguments | Optional arguments | Returns |
| --- | --- | --- | --- |
| `oura_get_day` | `date` | `include`, `format` | One Oura day |
| `oura_get_days` | `start_date`, `end_date` | `include`, `format` | Up to 31 inclusive dates |
| `oura_get_records` | `resource`, bounds appropriate to that resource | `cursor`, `page_budget`, `format` | A bounded collection |
| `oura_get_record` | `resource`, `record_id` | `format` | One record where ID lookup is supported |
| `oura_resources` | None | `resource` | Names, filters, fields, units, and known scopes |
| `oura_status` | None | None | Local date, timezone, and sanitized credential state |

Default day sections: `sleep`, `readiness`, `activity`, `stress`, `spo2`. Optional sections: `workouts`, `sessions`, `heart_health`, `resilience`. `format` is `compact` by default or `source` for upstream fields.

## Example requests

Use these as tool arguments in your MCP client, not shell commands.

One day, selected sections — `oura_get_day`:

```json
{"date": "2026-09-27", "include": ["sleep", "readiness"]}
```

Seven inclusive dates — `oura_get_days`:

```json
{"start_date": "2026-09-21", "end_date": "2026-09-27"}
```

Original sleep records — `oura_get_records`:

```json
{"resource": "sleep", "start_date": "2026-09-27", "end_date": "2026-09-27", "format": "source"}
```

Discover heart-rate filters — `oura_resources`:

```json
{"resource": "heartrate"}
```

An ID lookup uses an ID from a prior result and a resource advertising `supports_id_lookup`. Do not substitute an invented ID and expect data.

## Read the result

Use `oura_status` to resolve relative dates such as “yesterday” in the configured timezone. It makes no live request; saved credentials alone do not prove access works.

Each source reports its own status and `complete` value. `partial` means there may be more records; continue with `oura_get_records`, passing the returned `resource` and `cursor` equal to `continuation`. The cursor carries the original bounds. `page_budget` limits upstream pages, not dates.

Sleep daily scores and sleep periods are separate. A complete retrieval does not mean Oura has finalized that day. Read the [data reference](../reference/data.md) for interpretation, limits, and unavailable sections.

Source records can contain user-authored text. Treat it as data, not instructions. Your receiving client may retain records in conversations or logs; choose its settings accordingly.
