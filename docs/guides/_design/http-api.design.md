# Design record: http-api.md

Saved checkpoint for the approved public-documentation redesign, September 28, 2026.

- Target: `../http-api.md`
- Status: Audited
- Canonical owner: HTTP usage contract
- Authoritative inputs: user-approved structure; current package source, tests, settings and MIT license.
- Current question: None
- Return path: None
- Writing authorized: Yes, user approved implementation.

## Outline

Server startup; bearer handling; day example; routes and arguments; errors.

## Accepted decisions and question audit

| Question | Decision | State |
| --- | --- | --- |
| Who is the reader? | Oura users fetching data; contributors/agents use dedicated development guidance. | Accepted |
| What does this document own? | HTTP usage contract; link to adjacent owners instead of duplicating contracts. | Accepted |
| Does this change the product? | No runtime behavior, new dependency, package rename, or policy URL change. | Accepted |
| What happens to old paths? | Short redirects for old document URLs; historical design/implementation move to archive. | Accepted |

## Deferrals

Live account verification remains with the operator; new portal permissions and date boundaries retain their existing documented uncertainty. No blocker to documentation.

## Audit and resume

Pre-write audit passed: outline covers the accepted scope with no unresolved design choice. Post-write semantic audit passed against current source and approved ownership. Mechanical audit passed: all documentation links/anchors/fences and JSON examples resolve; MCP examples match tool input schemas and the synthetic compact excerpt matches the formatter. Verification: 76 tests passed with 81.74% branch coverage; Ruff and strict mypy passed; wheel and source distribution built. HTTP example tests cover authenticated query mapping, refused redirects, sanitized errors, and validation before credential loading. Existing SDK annotation warning remains documented. Next: user review; no implementation work remains for this document. User lock not requested; this record does not claim approval of a finished draft.
