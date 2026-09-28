# Setup and security

Install uv using its [official platform instructions](https://docs.astral.sh/uv/getting-started/installation/). Use a native Python runtime for your platform; this project is tested with Windows x64 Python 3.12. Run `uv sync --locked` in the checkout.

## Desktop login

Run `uv run oura-connector ui`, or open the **Oura Connect** desktop shortcut. The first screen has an Oura developer-portal link, a button to copy the exact callback URL, masked client-secret entry, and timezone selection. Save and connect once; future launches restore the saved connection view.

Oura authentication happens only in the browser. The app never asks for or stores your Oura password. Its worker keeps the window responsive during sign-in. Cancel stops waiting; closing during an operation waits for it to finish safely. The saved view distinguishes stored credentials from a successful live connection check.

**Disconnect** removes only the saved OAuth token file under the refresh lock. It does not delete health data, erase app configuration, or revoke the grant on Oura's website. Existing in-flight data requests may finish; subsequent requests must sign in again. For full provider revocation, remove access in Oura's portal.

Windows uses DPAPI CurrentUser encryption plus restrictive file permissions for client secrets, HTTP bearer tokens, OAuth tokens, and temporary OAuth state. Other programs running as your Windows account may still decrypt them. Protected plaintext files created by the earlier CLI are encrypted when the desktop app opens; their paths and values stay the same. No .env files are imported. Reconfigure rather than copying encrypted files to another Windows account or PC.

## Oura authorization from the CLI

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

Use `uv run oura-connector --config C:/path/to/config.toml status` for another location. Credentials stay beside that config. Secret files are protected for the current Windows user and SYSTEM; POSIX files use owner-only permissions. Windows secret payloads are encrypted with DPAPI CurrentUser. On other operating systems they are owner-only files and are not encrypted by this application.

Setup refuses to overwrite existing configuration or credentials. Edit non-secret settings in `config.toml`. After changing OAuth applications, disconnect locally, then enter the new details in the desktop app and connect again. Restart existing MCP/HTTP processes after changing application settings. The connector does not import old settings, read `.env`, or migrate/delete existing credentials.

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
