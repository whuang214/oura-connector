# Run your own copy

Oura Connector is source code you run yourself. The normal setup is one person, their own computer, their own Oura account, and their own developer application. Cloning the project does not create an account with the maintainer or grant access through the maintainer's OAuth app.

## Start here

1. Clone the repository and install the locked Python dependencies with uv, as shown in the [README](../README.md).
2. Create your own application in the [Oura developer portal](https://developer.ouraring.com/applications), following the [registration guide](app-registration.md).
3. Use your own monitored Contact Email. Register the callback URL shown by your local app. Keep your client secret private.
4. Enter your app's credentials in Oura Connect and authorize your own account in Oura's browser page.
5. Choose the local clients that may receive your records. Review their privacy and retention settings before sending data.

## Who is responsible for what

| Party | Role |
| --- | --- |
| Upstream maintainer | Publishes code and documentation under MIT; does not run your installation or promise support. |
| You, the operator | Register and secure your developer app, choose permissions and clients, maintain your installation, and handle your copies of data. |
| Oura | Operates its account, authorization, and API services under its own terms. |
| Receiving clients | Process or retain returned data according to their own behavior and settings. They may use remote services even though the connector runs locally. |

## Policies for your developer registration

The upstream [Privacy Policy](../PRIVACY.md) describes the unmodified local software. The [Terms of Service](../TERMS.md) describes the project and its software-use conditions. The [MIT license](../LICENSE) is the software license.

For an unchanged personal installation, review those documents against your actual setup before referencing them in your registration. The Contact Email is always yours. A public project policy does not make the maintainer the operator of your app, and a working URL does not guarantee acceptance by Oura.

If you modify data collection, add storage or telemetry, host the connector, or serve other people, publish your own policies describing your actual operation. A practical starting point is to copy and adapt the project policies in your own public repository or website. Identify your app and operator, give a monitored contact, describe collection, recipients, storage and deletion, and remove statements that are no longer true. Keep software copyright and license notices; do not imply upstream endorsement.

The current connector is designed for local use. Its HTTP interface is loopback-only. Hosting it for other people requires a separate design, not just replacing policy URLs.

## What the license does

MIT includes warranty and liability disclaimers. These documents do not guarantee immunity from claims, certify regulatory compliance, or override mandatory legal rights or provider agreements. Obtain jurisdiction-specific legal advice if you need a legal risk assessment or plan to operate a service for others.

## Stop using it

Disconnect in the app to remove its local OAuth tokens, revoke the application's access with Oura, and remove local setup files if desired. Remove outputs from receiving clients separately. The [setup guide](setup.md#local-files) lists the stored files and locations.
