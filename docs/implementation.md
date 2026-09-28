# Implementation record

## Authority and state

The user approved docs/design.md on September 28, 2026. Destination: whuang214/oura-connector (formerly oura-data-api). Base commit: 341d0db. Branch: overhaul. Initial checkout clean. No current integrations need compatibility. Keep the old remote oura-mcp repository intact unless separately requested.

Implementation is authorized. Dependency installation/addition/removal requires specific approval. Request pending: add mcp==1.28.1, retain/install the existing declared runtime/build/dev dependencies and compatible transitive dependencies from PyPI using uv with installed Windows x64 Python 3.12.13 in this project's .venv. No manifest edits or dependency installs before approval. No new runtime requested.

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

## Current checkpoint

Completed: cloned renamed repo; inspected status/history/docs/manifest/source; verified native tool route; generated ignored navigation graph; reviewed official uv and MCP setup documentation; saved approved design and audited sequence.

Pending: dependency approval. Next action once approved: use official uv dependency commands, resolve and lock the local environment, and implement/verify the foundation. No application edits or runtime tests yet.
