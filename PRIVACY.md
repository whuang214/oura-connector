# Privacy

Oura Connector runs locally and retrieves records from Oura only when requested. It has no hosted backend, telemetry, advertising, Google Sheets integration, or persistent health-data cache.

OAuth client credentials and rotating tokens are stored in protected local files outside the repository. They are not encrypted by this application. Use operating-system disk encryption and restrict access to your user account.

Oura receives authenticated API requests. MCP and HTTP clients receive requested records and may retain them in logs, conversations, or their own storage. Review those clients' privacy settings. Data returned by Oura can contain personal details and user-authored text.

Diagnostics avoid printing tokens and health records. HTTP access logging is disabled by the CLI. Do not enable verbose third-party network logging around real credentials or commit credentials, cursors, or health outputs.

Revoke the application's access through Oura when you no longer need it. Removing this source repository does not revoke Oura access or delete credentials stored in your user configuration directory.
