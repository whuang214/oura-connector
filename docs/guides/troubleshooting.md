# Troubleshooting

Start with sanitized local diagnostics from your checkout:

```powershell
uv run --locked oura-connector status
uv run --locked oura-connector doctor
```

`status` reports the configured date/timezone and credential presence. `doctor` also validates configuration and protected-file access. Neither fetches Oura records. Avoid sharing account-specific paths or identifiers unnecessarily.

After signing in, explicitly test live access:

```powershell
uv run --locked oura-connector doctor --live
```

This probes today's daily sleep collection and prints status rather than health records. An empty successful result still verifies that request. It does not prove every optional permission works.

## Common problems

| Symptom | What to check |
| --- | --- |
| `uv sync` removes pytest, Ruff, or other development tools | Update your checkout and run `uv sync --locked`. Development tools now belong to uv's default `dev` group. Older checkouts stored them in an optional extra that plain sync removed. |
| Root launcher does not open the window | Run `uv run --locked oura-connector ui` from the checkout to see the error. Confirm `uv` is installed and `uv sync --locked` succeeds. If Windows blocks PowerShell scripts, use the uv command directly; the launcher does not change execution policy. |
| MCP client cannot launch uv | Configure the full uv executable path and correct absolute checkout directory. |
| MCP works in a terminal but not in the client | Check the user account and `--config` profile. Restart the client process. |
| Credentials saved but access fails | Run the live probe; reopen Oura Connect and authorize again if required. |
| Browser reports redirect mismatch | Register the exact callback shown in Oura Connect, including `localhost`, port, and `/callback`. |
| Callback port busy | Close the other listener, or choose another localhost port in settings and register the same URI with Oura. |
| Saved credentials cannot be decrypted | On Windows, use the original Windows account/computer. Reconfigure on a new account or machine rather than copying encrypted files. |
| Unknown setting or invalid timezone | Compare with the [configuration reference](../reference/configuration.md); use an IANA timezone. |
| HTTP 401 | Use the generated local HTTP token, not the Oura secret/token; match server and client profiles. |
| HTTP 403 | The API is for local programmatic requests and rejects browser-origin requests. |
| Connection refused | Start `oura-connector serve` and check the configured host/port. |
| A section is `unavailable` | Inspect its sanitized error and granted permissions. One denied source does not imply all sources failed. |
| A result is `partial` | Resume with its continuation; reduce the range or sections if a response limit was reached. |
| Data is `empty` | Complete retrieval succeeded with no records. Check the Oura-assigned date and synchronization; do not substitute zeros. |
| Sleep differs from the Oura app | Read [sleep and formatting](../reference/data.md#sleep-and-formatting); API values and app aggregation can differ. |

## Alternate profiles

The global `--config` option goes before the subcommand:

```powershell
uv run --locked oura-connector --config C:/path/to/config.toml doctor --live
```

Repeat the same option in MCP/server startup. Configuration files are TOML; the connector never imports `.env` files.

## Known verification limits

Windows x64 Python 3.12 is verified. Other OS/Python combinations are not claimed tested. The three newer portal permission labels and certain upstream date boundaries still need live-account verification; see [setup](setup.md#permissions) and [data](../reference/data.md#dates-and-limits).

The locked MCP SDK can emit a pydantic-settings incomplete-annotation warning. Offline protocol tests pass; the warning is tracked rather than suppressed.

## Reporting a problem

Use the [issue tracker](https://github.com/whuang214/oura-connector/issues) with the command/tool, version or commit, OS, expected result, and sanitized error. Reproduce with synthetic records where possible. Never attach credentials, real `.env` files, authorization headers, cursors, or health records.
