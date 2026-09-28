> Historical record of the original overhaul. For current usage, start with the [documentation](../README.md). Paths and completion notes below describe that work.

# Oura Connector — Approved design

Updated: September 28, 2026. Status: approved for implementation; implementation tracked in implementation.md.

## 1. Purpose and accepted direction

One local Python package retrieves Oura data and exposes it through MCP and an optional HTTP API. Both interfaces call the same service directly. MCP does not start or depend on an HTTP server.

Accepted: consolidate the two repositories, use `uv`, remove legacy compatibility, and use the working name `oura-connector` without version branding. Remove Sheets integration, analytics, comparisons, baselines, coaching, and sync bundles. Existing credentials and personal data are not deletion targets.

The connector retrieves and formats measurements and scores that Oura already provides. It does not reconstruct Oura's algorithms. Date-first access is the primary user experience. The user approved this contract and its final plan on September 28, 2026.

## 2. What the user asks for

| Request | Tool behavior |
| --- | --- |
| “Get my Oura data for September 27.” | Retrieve the default sections for that Oura date. |
| “Get my last seven days.” | Retrieve a range once per required resource, then group records by Oura date. No weekly averages or comparisons. |
| “Only sleep and readiness for yesterday.” | Retrieve only those sections. |
| “Show the full record for that sleep.” | Fetch the identified sleep record in source mode. |
| “Show heart-rate readings from 2–4 PM.” | Retrieve the explicit timestamp interval. |
| “Why is my connection failing?” | Inspect sanitized connection status; use the CLI doctor for deeper diagnostics. |

Natural-language interpretation belongs to the assistant. Tools accept explicit ISO dates and offset-aware timestamps. Status reports the configured timezone and current local date so the assistant can resolve “today” without using an accidental UTC date. “Last night” ordinarily maps to the date of waking, but unusual shifts or travel may need clarification.

## 3. MCP tools

Expose six tools. Retrieval tools are read-only with respect to Oura data; reading may refresh local OAuth credentials. No tools delete health records, write annotations, or provide coaching.

| Tool | Inputs | Returns and behavior |
| --- | --- | --- |
| `oura_get_day` | `date`, optional `include`, `format` | One day containing independently reported sections. Primary everyday tool. |
| `oura_get_days` | `start_date`, `end_date`, optional `include`, `format` | The same day structure for each requested date, ordered ascending. Dates are inclusive. No aggregation. |
| `oura_get_records` | `resource`, resource-appropriate date or timestamp bounds, optional `cursor`, `page_budget`, `format` | Resource records with explicit pagination completeness and continuation. Also supports resources without dates. |
| `oura_get_record` | `resource`, `record_id`, optional `format` | A single record, only for resources with official ID lookup support. |
| `oura_resources` | Optional `resource` | Available resources, valid filters, compact fields, units, ID-lookup support, and known access requirements. Discovery does not fetch personal data. |
| `oura_status` | No inputs | Local date/timezone, credential presence/expiry, and sanitized connection state. Local status alone does not claim a successful live request. |

`format` is `compact` by default or `source`. The day tools use the same internal range function; the single-day tool is a convenience wrapper.

Proposed bounds: day bundles cover at most 31 inclusive days; individual date resources at most 90 days; timestamp resources at most seven elapsed days. Page, record, byte, and concurrency limits are explicit validated settings. Exact operational defaults will be verified against fixtures and upstream behavior before release.

## 4. What a day contains

Proposed default: `sleep`, `readiness`, `activity`, `stress`, and `spo2`. The user can change the default sections in settings or override them per call. An empty include list is rejected; unknown sections fail validation before requests begin.

| Section | Upstream collection | Content |
| --- | --- | --- |
| `sleep` | `daily_sleep` and `sleep` | Daily Oura score/contributors plus separate sleep-period records. |
| `readiness` | `daily_readiness` | Oura score, contributors, temperature fields. |
| `activity` | `daily_activity` | Score, steps, calories, activity durations, and selected source fields. |
| `stress` | `daily_stress` | Oura stress/recovery durations and source classification. |
| `spo2` | `daily_spo2` | Oura oxygen-saturation result and breathing-disturbance fields. |
| `workouts` — opt-in | `workout` | Individual workout records. |
| `sessions` — opt-in | `session` | Individual session records. |
| `heart_health` — opt-in | `daily_cardiovascular_age` and `vO2_max` | Oura-provided cardiovascular-age and fitness records. |
| `resilience` — opt-in | `daily_resilience` | Source resilience data when accessible. |

Tags, rest-mode intervals, sleep timing, ring information, personal information, and dense heart-rate/battery time series remain available through the resource tools. They are not automatically included in a day. This avoids inventing date joins for interval records and exposing unrelated personal fields.

For the default bundle, five sections require six collections. A range request fetches each collection over the range, following its pages; it does not run six requests separately for every day. Section requests use bounded concurrency. Different resource responses are not an atomic snapshot of Oura's database.

## 5. Sleep: what is calculated, and by whom?

**Oura calculates sleep. The connector reads the results.** Oura describes its scoring as proprietary and based on multiple sleep contributors. Its daily score can incorporate naps. We do not average contributor scores or rebuild the daily score. [Oura Sleep Score](https://support.ouraring.com/hc/en-us/articles/360025445574-Sleep-Score)

Two upstream resources answer different questions:

- `daily_sleep` provides the daily score and contributor scores.
- `sleep` provides individual periods, their timestamps, durations, stages, heart measurements, and classifications.

The daily score is shown once in `sleep.daily`; periods appear in `sleep.periods`. We do not attach the daily score to every nap as though it were a per-period score.

| Displayed value | Source and connector behavior |
| --- | --- |
| Sleep score | Copy `daily_sleep.score`. No recalculation. |
| Contributor scores | Preserve in a separate `contributors` object; these are scores, not durations or measured HRV. |
| Total sleep for a period | Copy `sleep.total_sleep_duration` in seconds. Optional display text converts units only. |
| Time in bed | Copy `time_in_bed`; never substitute it for missing sleep duration. |
| Deep, REM, light, awake | Copy the corresponding period durations with explicit seconds units. |
| Efficiency | Copy Oura's `efficiency`. Do not recompute and overwrite it. |
| Sleep latency | Copy `latency` in seconds. |
| Average HRV | Copy `average_hrv`, labeled milliseconds; do not substitute the readiness HRV-balance contributor score. |
| Average/lowest sleeping heart rate | Copy the API fields, labeled beats per minute. |
| Breathing rate | Copy `average_breath`, labeled breaths per minute. |
| Bedtime and wake time | Preserve source timestamps and offsets. |

For example, 27,000 seconds may display as `7h 30m`; the numeric source remains 27,000. If the source value is null, both numeric and formatted values remain null. Formatting never estimates absent measurements.

### Multiple periods and naps

Preserve separate periods and Oura's original `type`. Do not sum periods into a new daily sleep total, average their HRV, infer a nap from duration, or pick a longest period and label it Oura's official main sleep.

The current schema distinguishes `long_sleep`, `sleep`, `late_nap`, `rest`, and `deleted`. Compact mode presents active sleep types as sleep periods. Rejected `rest` and `deleted` records are excluded from that list with their omitted counts disclosed; source mode preserves them. Unknown future types are returned with a warning, rather than silently dropped. [Official API schema](https://cloud.ouraring.com/v2/static/json/openapi-1.41.json)

Nap timing can affect when Oura updates daily scores. The connector reads current source results and does not manually apply `sleep_score_delta` or `readiness_score_delta`. Those fields remain accessible as source data. [Oura Nap Detection](https://support.ouraring.com/hc/en-us/articles/1500009653181-Nap-Detection)

### Why a number might differ from the app

The current API schema explicitly distinguishes its average and lowest sleep heart-rate calculations from the app's aggregation of five-minute samples. Preserve API values and explain their source; do not alter them to imitate the app. Historical results may also change after Oura recalculation. A fresh retrieval is not proof that Oura has finished updating a day. [Official API schema](https://cloud.ouraring.com/v2/static/json/openapi-1.41.json)

## 6. Date and timezone behavior

Oura documents different day boundaries: sleep uses 6 PM–6 PM, activity uses 4 AM–4 AM, and calendar days use midnight boundaries. A daily bundle joins Oura-assigned dates, not identical wall-clock windows. [Oura day definitions](https://partnersupport.ouraring.com/hc/en-us/articles/29160913203219-Understanding-the-Different-Types-of-Oura-Days-in-Oura-API-Data)

Rules:

1. Use the source `day` for daily records and sleep periods. Never relabel all records based on timestamp dates.
2. Preserve original timestamp offsets, including during travel and daylight-saving changes.
3. Use configured timezone only to resolve shortcuts and define explicit local timestamp queries; it does not override Oura's day assignment.
4. Define connector date ranges as inclusive. Translate to upstream endpoint semantics in one place and filter returned records by their source day.
5. Verify upstream single-day and end-boundary behavior before implementation is finalized. Do not blindly copy community workarounds that widen every request.
6. Do not mark a past day finalized just because midnight has passed. Report retrieval time and source availability.

## 7. Response and failure contract

Every requested day appears, including days with no records. This means an empty day is visible without fabricating measurements.

Each underlying collection has `status`, `records`, `complete`, and, when needed, `error` or `continuation`. Status is `ok`, `empty`, `partial`, `unavailable`, or `error`. A successful empty result is never described as an authorization error or as zero sleep.

Sleep has independent `daily` and `periods` outcomes. A failed score request must not erase successful period records. The same independence applies across all sections.

Day bundles automatically follow pages within limits. If a budget is reached, disclose the affected collection and provide a continuation usable by `oura_get_records`. Records already retrieved remain usable. Per-day absence in an incomplete collection must be marked uncertain, not definitively empty. Completeness describes retrieval only, not whether Oura's physiological data is final.

Compact mode keeps IDs, assigned days, relevant measurements, and unit labels. Dense sample arrays are omitted by default. Source mode preserves complete upstream records within the same explicit size limits. If even one record is too large, return an actionable size-limit error; never silently cut JSON or claim a complete record.

Example shape, with synthetic values and only the sleep section shown:

```json
{
  "date": "2026-09-27",
  "format": "compact",
  "retrieved_at": "2026-09-28T14:00:00Z",
  "sections": {
    "sleep": {
      "daily": {
        "status": "ok",
        "complete": true,
        "records": [{"id": "example-daily", "day": "2026-09-27", "score": 82}]
      },
      "periods": {
        "status": "ok",
        "complete": true,
        "records": [{
          "id": "example-period",
          "day": "2026-09-27",
          "type": "long_sleep",
          "total_sleep_seconds": 27000,
          "total_sleep_display": "7h 30m",
          "average_hrv_ms": 48,
          "average_heart_rate_bpm": 55,
          "omitted_fields": ["heart_rate", "hrv", "movement_30_sec"]
        }]
      }
    }
  }
}
```

The illustration does not specify every compact field. The resource registry will expose the definitive field list; unknown upstream fields remain accessible in source mode.

## 8. HTTP and local operation

| HTTP route | Shared operation |
| --- | --- |
| `GET /days/{date}` | `oura_get_day` |
| `GET /days?start_date=...&end_date=...` | `oura_get_days` |
| `GET /records/{resource}` | `oura_get_records` |
| `GET /records/{resource}/{record_id}` | `oura_get_record` |
| `GET /resources` | `oura_resources` |
| `GET /status` | `oura_status` |
| `GET /health` | Process liveness only |

HTTP binds to loopback by default and protects data routes. MCP uses stdio. Both call the same Python functions and produce equivalent data contracts. No internal HTTP hop or managed child API process is needed.

No persistent health database, background sync, or scheduled tasks in the initial design. OAuth credentials persist in protected local storage. Normal settings are separate from secrets and from the repository. CLI commands cover setup, login, status, doctor, MCP launch, and optional HTTP launch.

## 9. Repository and customization

Use one `pyproject.toml` and `uv.lock`. Keep the package shallow: `auth.py`, `client.py`, `config.py`, `models.py`, `resources.py`, `service.py`, `formatting.py`, and `interfaces/` for MCP, HTTP, and CLI. Tests and synthetic fixtures sit under `tests/`; concise guides under `docs/`; non-secret examples under `examples/`.

The resource registry owns upstream paths, filter kinds, ID support, compact fields, and unit labels. Adding a resource should not require duplicating its behavior across interfaces.

Customizable: default day sections, compact fields, display timezone, operational limits, and HTTP settings. Per-call `include` and `format` override defaults. No configurable scoring system, arbitrary expression execution, or plugin framework.

## 10. Verification and implementation sequence

1. Establish a working checkout and inspect local instructions, Git state, and existing dependencies. Preserve unrelated work. Choose the destination repository without deleting the other remote repository.
2. Audit reusable authentication/retrieval code and the current upstream schema. Finalize field mappings and date-boundary tests.
3. Implement the shared resource client, secure OAuth, pagination, and normalized errors.
4. Implement day/range assembly and pure formatting functions.
5. Add thin MCP/HTTP interfaces and unified CLI setup/diagnostics.
6. Remove old analytics, Sheets, process-management, and compatibility code from the selected replacement checkout. Exact targets must be reviewed; recursive deletion requires separate confirmation under the user's global rules.
7. Verify and document Windows x64 operation. Commit each passing wave locally; do not push without instruction.

Required tests: midnight/DST boundaries; overnight sleep and late naps; multiple sleep periods; null versus zero; score versus measurement fields; denied permissions; successful empty responses; partial collections; byte/page limits; token refresh races; and equivalent API/MCP results. A seven-day bundle must fetch ranges per resource, not repeat the same fetch for every date.

Fixture and protocol tests come first. Live verification is separate: report precisely what ran, never claim app-value parity or live reliability based only on fixtures. The user subsequently approved the required and future Python libraries for this work on September 28, 2026. Real `.env` files must not be read or modified.

## 11. Review point and return path

Current task: implement the approved day-first tool surface and sleep behavior. Approval is not a record of completed or verified changes.

Accepted: day bundles with the listed default sections, source-assigned dates, and separate sleep periods without calculated daily totals. Destination repository is whuang214/oura-connector, renamed by the user from oura-data-api. Python dependencies were subsequently approved by the user. No extra analytics are implied by formatting or grouping.

Resume from this document. Preserve the accepted single-package, retrieval-only direction; do not restart comparison shopping or reintroduce the removed features.


## 12. Desktop connection extension

On September 28, the user requested a login UI like their Bitwarden Connect app, with local saving. Oura Connect adds a native desktop window for first-time OAuth app details, browser consent, saved-connection status, connection checks, and local disconnect. It uses the same core auth and data code. Windows saves are encrypted with DPAPI CurrentUser in addition to restrictive permissions. No Oura password is handled and no health dashboard or analytics were added. Closing preserves sign-in; disconnect removes the local OAuth token file and keeps app configuration. First app setup or credential changes require restarting any already-running MCP/HTTP process.
