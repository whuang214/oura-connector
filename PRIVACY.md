# Privacy Policy

Updated September 28, 2026. Applies to the local software in the oura-connector repository, including registrations using the display name Personal Ring Connector.

## Data and purpose

Oura Connector runs locally and retrieves records from Oura only when requested. It has no hosted backend, telemetry, advertising, Google Sheets integration, or persistent health-data cache.

Requested records may include sleep, readiness, activity, heart rate, workouts, sessions, tags, blood oxygen, stress, heart health, device details, and personal profile information. Availability depends on your permissions and the requested collection. The connector does not retrieve every category simply because you sign in.

## Local storage

OAuth client credentials and rotating tokens are stored in protected local files outside the repository. On Windows, payloads are encrypted with DPAPI CurrentUser as well as protected by file permissions. Other platforms use owner-only files without application encryption. Software running as your own Windows user may access DPAPI-protected secrets; restrict access to your account. The desktop login opens Oura in the browser and never handles your Oura password.

## Recipients

Oura receives authenticated API requests. MCP and HTTP clients receive requested records and may retain them in logs, conversations, or their own storage. Review those clients' privacy settings. Data returned by Oura can contain personal details and user-authored text.

The project maintainer does not receive records through a hosted project service. You control which local clients receive output. This software does not train AI models. See the [registration guide](docs/app-registration.md#current-provider-restriction) before sending API data to any AI client.

## Retention and removal

Credentials remain until removed; OAuth tokens rotate during use. Disconnect in the desktop app deletes the local OAuth token file, but keeps app settings and the client secret. Closing the window keeps the saved sign-in. To remove the complete local setup, close connector processes and delete its configuration directory: `%LOCALAPPDATA%/oura-connector` on Windows, or the configured XDG directory on other platforms. A custom configuration may use another location.

Revoke the application's access through Oura when you no longer need it. Removing this source repository does not revoke Oura access or delete credentials stored in your user configuration directory.

Delete any retained exports, logs, or conversations separately in the clients that created them. Local removal does not delete your source records from Oura.

## Contact

Contact the person listed in your developer application's Contact Email field about that registration. For software questions, use the [project issue tracker](https://github.com/whuang214/oura-connector/issues). Do not post credentials or health records in public issues.
