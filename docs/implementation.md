# Implementation record

## Authority and state

The user approved docs/design.md on September 28, 2026. Destination: whuang214/oura-connector (formerly oura-data-api). Base commit: 341d0db. Branch: overhaul. Initial checkout clean. No current integrations need compatibility. Keep the old remote oura-mcp repository intact unless separately requested.

Implementation is authorized. Dependency installation/addition/removal requires specific approval. User approved all Python libraries needed for this overhaul on September 28, 2026. Approved: add mcp==1.28.1, retain/install the existing declared runtime/build/dev dependencies and compatible transitive dependencies from PyPI using uv with installed Windows x64 Python 3.12.13 in this project's .venv. Approval received before manifest edits and installation. No new runtime requested.

No real .env files or private state may be read, copied, modified, or indexed. Existing legacy source removal is authorized by the overhaul; remove exact reviewed tracked files individually, not by recursive deletion. Preserve Git history. No pushes or remote deletion.

## Audit findings

- Current API has no lockfile; it has a FastAPI/Pydantic/HTTPX stack, pywin32 for Windows token protection, and a substantial fixture-based test suite.
- Reuse the tested protected-file and token-refresh concepts in auth.py. Eliminate its coupling to legacy .env-only settings and analytics.
- Provider registry already maps the intended resources. Verify against the official current schema before carrying mappings forward.
- Existing service repeats full-range fetches for analytics. Replace with one bounded collection retrieval per selected resource, shared across days.
- Existing fixture data is documented synthetic. Reuse only source-shaped fixtures needed by retrieval tests.
- No repository AGENTS.md is tracked. Global user rules apply; old docs' compatibility and pip rules are superseded by explicit overhaul and uv requirements.
- Native graph extraction succeeded. Graphify/Serena MCP query tools are unavailable in this session; source inspection is the evidence source.

## Audited work sequence

1. Foundation: approved design/record; dependency resolution after approval; package settings and error types; protected credential storage; OAuth state/PKCE and refresh locking. Verify settings, atomic storage, permission failures, callback mismatch, and rotated tokens.
2. Retrieval: resource registry; streamed response-size bounds; timeout/retry policy; resource-specific argument validation; pagination with resumable state. Verify empty pages, repeated cursors, next-page errors, range filtering, and record limits without skips.
3. Day assembly: retrieve six default collections for the entire requested range; group by source day; independent sleep daily/period statuses; partial day uncertainty; pure compact/source formatting. Verify multiple sleeps, deleted/rest types, null/zero distinctions, no aggregation, and bounded response sizes.
4. Interfaces: six MCP tools; matching HTTP operations; common service factory/lifecycle; local CLI setup/login/status/doctor/mcp/serve. Verify authentication on data routes, tool validation, API/MCP parity and stdio startup with synthetic data.
5. Cleanup/documentation: replace old code, tests and docs with the new structure; retain license; update privacy/terms to actual behavior; uv-based setup; dependency/field references. Verify no old package imports or obsolete commands.
6. Final audit: focused and complete tests, Ruff, mypy, wheel build/content check, Windows startup and protocol smoke tests. Live access requires user OAuth and must be reported separately. Commit passing coherent waves locally, never failing work.

## Design details to enforce

- Explicit dates on tools; offset-aware timestamps for time-series resources. UTC conversion must not relabel Oura days.
- Compact is selection/renaming/units only; source preserves upstream fields. Do not average, choose main sleep, or total periods.
- Default day sections: sleep, readiness, activity, stress, spo2. Extras are explicit.
- Pagination truncation always exposes completeness and continuation; missing records from incomplete collections are not confidently empty.
- Small default tool surface; no framework for plugins/rules or persistent health cache.
- Preserve transport security and exact origin boundaries; errors must not echo bearer tokens or upstream payloads.

## Final checkpoint

Implementation and offline verification complete on September 28, 2026. The public package and command are oura-connector. One service serves six MCP tools and the optional authenticated loopback HTTP API. The legacy package, analysis, old CLI commands, old fixtures and obsolete documentation were removed as 59 exact, individually reviewed tracked file deletions. No recursive deletion, credential migration, remote deletion, or push was performed.

Delivered:

- TOML configuration outside the repo, protected credentials, OAuth state/PKCE, atomic rotation and refresh locking.
- Registry of 19 official collections, bounded streaming/retries, source lookup, and resumable pagination including mid-page continuation with drift detection.
- Inclusive day/range tools, per-resource range fanout, independent collection outcomes and source-assigned day grouping.
- Compact formatting with unit labels, separate sleep scores and periods, null/zero preservation, disclosed rest/deleted omissions, and full source mode.
- Six stdio MCP tools, equivalent HTTP operations, and setup/login/status/doctor/mcp/serve commands.
- One pyproject.toml and uv.lock, short setup/data/development guides and a non-secret TOML example.

Verification:

- Baseline: 134 passed; the previous documentation inventory test rejected the newly approved design docs and was corrected before the foundation commit.
- Final: 62 tests passed, 82.62% branch-aware coverage (75% required).
- Ruff check and strict mypy passed for all 15 package modules; Ruff formatting applied.
- A real stdio subprocess initialized, advertised exactly six tools, returned local status, and rejected invalid input.
- Mock HTTP/MCP data parity, bearer/Host/Origin protection, actual loopback OAuth callback with forged and valid state, refresh races, pagination/retry/timeout/size boundaries, DST, and sleep cases passed.
- uv built the wheel and source distribution. Both member inventories were checked: no credentials, old package, analytics, or navigation artifacts. The wheel itself imported and executed CLI help in isolated Python mode. Documentation links resolve.
- No live Oura calls, personal health records, or real .env files were accessed. Test credentials and records are synthetic.

Known limits and follow-up:

- User login and live account verification remain outstanding. Run setup, login, and doctor --live, then inspect a known day.
- The official schema does not explicitly document end-date inclusivity. Primary reproduction at https://github.com/daveremy/oura-mcp/issues/5 reports exclusive upper dates on sleep/daily_activity/workout/session. The registry translates those four only and filters source days; mocks verify this, live boundary confirmation is still needed.
- FastMCP emits one upstream pydantic-settings incomplete-annotation warning with the locked dependency set. Protocol operation passed. No warning was suppressed.
- Windows x64 Python 3.12 was tested. Other platforms and Python versions are not claimed tested.
- Working branch: overhaul. Earlier passing implementation commits: 7501a19 (foundation), f5a9637 (retrieval), cf3c01e (days/formatting), 7ac26a5 (interfaces). Final cleanup/audit commit: c11e35f. Nothing pushed.

The user's September 28 approval covers future Python libraries for this work. No further implementation blocker remains; live account access is a user setup step, not a completed verification claim.


## Desktop login extension — September 28

User requested a nice local login UI like their Bitwarden Connect app. Inspected its public source and synthetic screenshots read-only. Adopted the native light-window flow, saved-connection dashboard, and CurrentUser DPAPI storage. No Oura password is handled; app credentials are entered once and user consent stays on Oura's website.

Implementation plan: add encrypted protected storage, reuse browser state/PKCE and refresh locking, add a thin desktop controller/window, add a hidden-console launcher/shortcut, verify synthetic UI and security flows, inspect previews, run full checks and commit locally. Python dependency approval already covers Tomli-W (settings writer) and development-only Pillow (preview capture). No changes to Bitwarden.

Navigation used source inspection because Graphify/Serena MCP query tools remain unavailable. The existing graph was not relied on after source changes.


Desktop extension verified: 72 tests passed with 81.74% coverage; Ruff and strict mypy passed; wheel and source distribution built. Synthetic setup and saved-connection previews were rendered and visually inspected. A hidden PowerShell launcher produced a visible window using an isolated nonexistent profile; closing exited cleanly without creating credentials. Fixed a UI test harness issue by sharing one Tcl interpreter, plus first-layout footer clipping and error recovery after a declined browser grant. No production account was used for tests. Existing SDK annotation warning remains unchanged. Final delivery includes a desktop shortcut and opening the real setup window for the user; entering app details and approving Oura remain user actions. No push.

## Portal registration documentation — September 28

User requested simple Privacy Policy and Terms of Service documents, screenshots of both, field instructions matching the supplied new-application form, and the developer portal URL update. Work stays on the overhaul branch. Audited sequence: verify current source/defaults and official references; update policies and quick registration guide; link into the detailed setup guide; change the desktop portal link; capture non-secret previews; check links, focused tests, lint, types, and diff; commit locally.

Completed: expanded PRIVACY.md and TERMS.md, added docs/app-registration.md with the supplied blank portal image and two browser-rendered policy screenshots, linked the existing synthetic login screenshot, updated README/setup guidance and desktop PORTAL. No new dependency, real credentials, registration submission, publication, or push. Graphify/Serena MCP query tools remain unavailable; targeted source inspection was used.

Verification: 10 desktop/CLI tests passed; Ruff and strict mypy passed. Both full-page policy screenshots were inspected for readable, complete content. Relative documentation links and diff whitespace were checked before commit. Remote publication and Oura's acceptance of GitHub policy URLs remain unverified.

New evidence changes the earlier MCP design assumptions: the current Oura API and MCP Agreement (effective June 8, 2026), section 4(d), restricts API-to-AI data use, and section 6(e) restricts application branding. Documented this in the user setup path rather than presenting the existing custom MCP path as approved. Proposed a neutral portal display name only; no package/UI rename or architecture change. Resolving the intended AI integration with Oura's current terms is the next unresolved design decision. The portal also exposes three permission labels absent from the eight-scope OAuth reference; exact new identifiers and live coverage remain unverified.
