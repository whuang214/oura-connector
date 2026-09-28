# Data contract

The interfaces retrieve records. They do not calculate sleep scores, readiness, baselines, trends, weekly averages, or recommendations.

## Discover available data

Use [MCP tools](../guides/mcp.md) or [HTTP endpoints](../guides/http-api.md) to retrieve records. Both return the same structures. This reference owns the shared meaning of those results.

`oura_resources` is the definitive resource/field map. Names follow the upstream API, including `sleep`, `heartrate`, `personal_info`, and case-sensitive `vO2_max`. It covers 19 collections. Some accept dates, some require offset-aware timestamps, ring configuration accepts no dates, and personal information is a singleton.

## Dates and limits

Day bundles cover 1–31 inclusive `YYYY-MM-DD` dates. Date collection queries cover at most 90 inclusive days. Timestamp queries cover at most seven elapsed days, require explicit offsets, and filter returned timestamps within the requested bounds. A week spanning daylight-saving changes may exceed seven elapsed days.

Day bundles join source `day`. They preserve timestamps and offsets; they do not reinterpret bedtime dates or force all Oura records into midnight-to-midnight windows. [Oura documents different day boundaries](https://partnersupport.ouraring.com/hc/en-us/articles/29160913203219-Understanding-the-Different-Types-of-Oura-Days-in-Oura-API-Data).

The official [schema](https://cloud.ouraring.com/v2/static/json/openapi-1.41.json) does not clearly specify end-date inclusivity. A [primary reproduction against Oura](https://github.com/daveremy/oura-mcp/issues/5) reports exclusive end dates for `sleep`, `daily_activity`, `workout`, and `session`. The registry requests the following date for those four, then filters by the original source-day interval. Other date resources keep supplied bounds. Mock tests verify this translation; live boundary confirmation remains outstanding. Interval resources without `day` retain Oura's filtering rather than inventing a date assignment.

See [configuration](configuration.md#limits) for operational defaults and upper bounds. A record/page that cannot fit returns an actionable error; JSON is never silently truncated. Bundle response limits can require fewer sections or a narrower range.

## Collection outcomes

Every requested day appears. Each source has:

- `resource`, `status`, `records`, and `complete`.
- `continuation` when retrieval stopped before completion.
- `error` when a request or limit failed, preserving earlier records.
- `omitted_records` and `warnings` for disclosed compact-mode filtering.

Status is `ok`, `empty`, `partial`, `unavailable`, or `error`. Empty requires successful complete retrieval. A missing day in an incomplete collection is uncertain and remains partial. Completeness describes retrieval, **not whether Oura has finalized the day**. The timestamp is retrieval time; separate collections are not an atomic snapshot.

Resume with `oura_get_records`, passing the returned `resource` and `cursor` set to `continuation`. Original bounds are carried in the cursor; supplied bounds must match. Continuations can resume within a page. A fingerprint detects page changes and asks for a restart rather than silently skipping records. Later pages can still change on Oura's side; no immutable snapshot is promised. Cursors contain query state and upstream pagination tokens, not OAuth tokens. Avoid publishing them.

## Sleep and formatting

`sleep.daily` contains the `daily_sleep` score and contributors. `sleep.periods` contains separate sleep records. Oura calculates both; the connector never averages contributors, adds naps to a score, sums periods, or chooses a main sleep.

Compact mode selects fields, labels units, and may add duration display text. `total_sleep_duration: 27000` becomes `total_sleep_seconds: 27000` and `total_sleep_display: "7h 30m"`. Null stays null; zero stays zero. Missing sleep duration is never replaced by time in bed. Contributor scores remain separate from measurements such as `average_hrv_ms`.

`rest` and `deleted` periods are omitted from compact collections with counts disclosed. `long_sleep`, `sleep`, and `late_nap` remain separate; unknown or null types remain with a warning. Explicit ID lookup still returns the identified record. Source format keeps all original fields and periods, including dense arrays, within response limits.

Compact records preserve IDs, days, types, timestamps and offsets. `omitted_fields` lists unselected fields. Customize selection using source field names under `[compact_fields]`; identity fields remain. Unknown upstream fields are accessible in source format.

The [official sleep schema](https://cloud.ouraring.com/v2/static/json/openapi-1.41.json) warns that average/lowest heart-rate calculations differ from the app's five-minute aggregation. Preserve the API value; app parity is not promised. See [Oura sleep scores](https://support.ouraring.com/hc/en-us/articles/360025445574-Sleep-Score) and [nap behavior](https://support.ouraring.com/hc/en-us/articles/1500009653181-Nap-Detection).
