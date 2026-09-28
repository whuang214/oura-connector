# Repository guidance

Oura Connector retrieves Oura data through a shared Python service with MCP and loopback HTTP adapters. Start with `docs/README.md`, `docs/development/architecture.md`, and the reference relevant to the change. `docs/archive/` is historical; `_design/` contains documentation authoring checkpoints, not runtime instructions.

## Work safely

- Inspect Git status and preserve unrelated work. Follow the user's dependency, commit, and push authorization; never force-push or bypass hooks without explicit authority.
- Use uv for Python workflows. Keep dependency changes deliberate and lockfile-backed. Do not install or change dependencies without the authority required by the current session.
- Never open, search, copy, or change real `.env` files. Never expose or commit credentials, health records, authorization headers, or continuation cursors. Tests and examples use synthetic data.
- Do not read a real user profile or call live Oura during routine verification. Use isolated temporary profiles and mock transports.
- Navigation tooling is optional; fall back to targeted source inspection if unavailable. Do not install tooling just to navigate.

## Source map

| Change | Owner |
| --- | --- |
| Resources, fields, units, filters | `src/oura_connector/resources.py` |
| HTTP transport, retries, pagination | `src/oura_connector/client.py` |
| Day assembly and shared operations | `src/oura_connector/service.py` |
| Compact/source formatting | `src/oura_connector/formatting.py` |
| OAuth and protected credentials | `src/oura_connector/auth.py`, `src/oura_connector/auth_models.py` |
| Settings | `src/oura_connector/config.py` |
| Login controller | `src/oura_connector/connection.py` |
| MCP / HTTP / CLI / desktop | `src/oura_connector/interfaces/` |

## Invariants

- Keep retrieval logic shared. MCP stdout is protocol-only; HTTP remains authenticated and loopback-only.
- Scores come from Oura. Do not add analytics, recompute scores, combine sleep periods, or reinterpret source days without an accepted design change.
- Preserve empty/partial/unavailable distinctions, continuation semantics, response bounds, and source-format fields.
- Preserve OAuth state, PKCE, atomic token rotation, locks, and protected storage. Windows credentials use DPAPI CurrentUser.
- Keep privacy and terms URLs stable. Update the owning documentation rather than duplicating contracts in multiple guides.

## Verification commands

`uv run --locked pytest`, `uv run --locked ruff check .`, `uv run --locked mypy`, and `uv build`.

See `CONTRIBUTING.md` for development dependencies, coverage, and platform caveats. Validate documentation links and runnable examples after reorganizing files. Report failures and unverified live/platform behavior explicitly.
