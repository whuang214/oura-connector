# Setup and security

Install uv using its [official platform instructions](https://docs.astral.sh/uv/getting-started/installation/). Use a native Python runtime for your platform; this project is tested with Windows x64 Python 3.12. Run `uv sync --locked` in the checkout.

## Oura authorization

1. Create an application in the [Oura developer portal](https://cloud.ouraring.com/oauth/applications).
2. Register the exact redirect URI `http://localhost:8765/callback`.
3. Run `uv run oura-connector setup --timezone America/New_York`. Enter the client ID and secret when prompted. Neither is placed in a command-line argument by default.
4. Run `uv run oura-connector login`. Approve access in the browser. The local listener waits up to three minutes.
5. Run `uv run oura-connector doctor --live`. This probes today's daily sleep collection and prints status, not health records. An empty successful result still verifies the request.

OAuth uses state validation and PKCE S256. Refresh tokens rotate under an interprocess lock and are replaced atomically. Declined optional scopes can make individual collections unavailable without erasing successful sections. Newer resource permissions are access requirements rather than invented OAuth scope names.

## Local files

Default directory: `%LOCALAPPDATA%/oura-connector` on Windows; `$XDG_CONFIG_HOME/oura-connector` or `~/.config/oura-connector` on other systems.

| File | Purpose |
| --- | --- |
| `config.toml` | Non-secret client ID, redirect, timezone, formatting, and limits |
| `credentials.json` | Client secret and generated HTTP bearer token |
| `tokens.json` | Rotating OAuth credentials bound to the configured client ID |
| `tokens.json.lock` | Cross-process token-refresh coordination |
| `tokens.json.oauth-session` | Temporary, one-shot state and PKCE verifier |

Use `uv run oura-connector --config C:/path/to/config.toml status` for another location. Credentials stay beside that config. Secret files are protected for the current Windows user and SYSTEM; POSIX files use owner-only permissions. They are protected local files, **not encrypted at rest**. Use operating-system disk encryption for that protection.

Setup refuses to overwrite existing configuration or credentials. Edit non-secret settings in `config.toml`. After changing OAuth applications, update the protected client secret locally and run login again. The connector does not import old settings, read `.env`, or migrate/delete existing credentials.

## MCP and HTTP

The MCP command is `uv run --locked oura-connector mcp`. It reserves stdout for protocol traffic and starts no API subprocess. Configure it as a local stdio server; see the root README.

HTTP is optional: `uv run oura-connector serve`. Only loopback hosts are accepted. Every route except `/health` requires the generated bearer token. The API rejects browser-origin requests and unknown Host values, disables access logs, and marks responses `no-store`. There is no public remote-server mode or unauthenticated documentation endpoint.

Neither interface persistently caches health data. MCP and HTTP clients may retain records in their own logs or conversations. Treat those clients as recipients of personal health information.

## Diagnostics

- `status` reports local timezone/date and credential presence. It makes no Oura request.
- `doctor` validates configuration and protected credential access.
- `doctor --live` tests one collection. It does not prove every optional scope is granted.
- `unavailable` usually indicates authorization or collection permission failure. Inspect the sanitized error and reauthorize if appropriate.
- `partial` means more data remains or a later request failed. Resume with the returned cursor.
- Unknown configuration keys are rejected. Check [example settings](../examples/config.toml).
- A busy callback port prevents login. Choose another localhost port in settings and register the exact same redirect in Oura.

Official references: [Oura OAuth](https://cloud.ouraring.com/docs/authentication), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.28.1), [uv](https://docs.astral.sh/uv/).
