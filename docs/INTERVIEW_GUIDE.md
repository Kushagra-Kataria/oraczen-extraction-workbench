# Read and explain the implementation

This project was built with AI assistance. Read each module before submission; these
notes guide that reading rather than replacing it.

## Reading order

| File | Responsibility |
| --- | --- |
| `backend/app/schemas.py` | Business validation, partial drafts, field metadata |
| `backend/app/config.py` | Defaults, bounded settings, secret handling, relative paths |
| `backend/app/tickets.py` | JSONL parsing, validation, duplicate rejection |
| `backend/app/providers/base.py` | Common async provider contract |
| `backend/app/providers/mock.py` | Text rules, quotes, missing facts, deliberate failures |
| `backend/app/extraction.py` | Validation, one retry, feedback, partial-value salvage |
| `backend/app/store.py` | Process-local storage and restart limitations |
| `backend/app/jobs.py` | Scheduling, shared concurrency cap, progress, cancellation |
| `backend/app/review.py` | Atomic corrections, versions, provenance, approval |
| `backend/app/routes.py` | HTTP boundaries and reviewed CSV |
| `backend/app/main.py` | Startup/shutdown resource ownership |
| `frontend/src/lib/types.ts` | API contracts and selectable field values |
| `frontend/src/lib/api.ts` | HTTP requests, configuration, field errors |
| `frontend/src/app/layout.tsx` | Root HTML, metadata, shared application layout |
| `frontend/src/app/page.tsx` | App Router inbox entry |
| `frontend/src/app/jobs/[id]/page.tsx` | Dynamic server route passes job ID to client workbench |
| `frontend/next.config.ts` | Same-origin API rewrites to the separate Python backend |
| `frontend/src/views/TicketsPage.tsx` | Filtered display and independent selection |
| `frontend/src/views/JobPage.tsx` | Polling, partial results, ordering, active record |
| `frontend/src/components/RecordEditor.tsx` | Local draft, server version, save/approval |
| `backend/app/providers/gemini.py` | Optional real JSON proposals and client cleanup |

## One ticket's journey

The route validates IDs and schedules a tracked job without waiting. A worker acquires
the shared semaphore before reporting running. The provider returns raw JSON.
`Proposal` checks the envelope; `Extraction` checks business fields. Validation errors
are returned to the provider for exactly one repair. Individually valid fields remain
editable if the full output fails. The worker stores a terminal result and the next poll
shows it. Human edits carry a version and only changed fields. Validation precedes
mutation; approval gates export.

Review routing depends on the six required business fields. Complete valid records
are Done even if evidence is inferred or notes contain ambiguity. Optional amount/date
may be null; after a failed repair, invalid optional values can be omitted from the
validated draft. A missing or invalid required value keeps the draft in Needs review.
Human edits follow the same rule. Done describes completeness, not export approval.

## Questions to be ready for

- **What does `await` do?** It allows other event-loop work while an async operation waits.
  It does not create a second process or make CPU-heavy work parallel.
- **Why `create_task`?** HTTP 202 must return before extraction ends. A strong reference
  keeps the task tracked and available for cancellation/shutdown.
- **Why the shared semaphore?** Each job having its own cap would multiply provider
  requests. Acquire before reporting running so waiting work stays queued.
- **Why exactly two attempts?** The brief allows one retry. Error feedback helps repair
  structure, but unlimited retries hide failures and waste capacity.
- **Can valid JSON be wrong?** Yes: it can fail the schema, or pass it but be factually
  incorrect. Human review addresses meaning, not just format.
- **Why JSON-mode strict validation?** ISO dates are wire-format strings, while amounts
  and booleans must retain their actual JSON types.
- **Why TypeAdapter for edits?** It reuses each field's schema for a partial correction;
  saving one repair does not require filling every other missing field.
- **Why a version?** Two reviewers can read the same snapshot. Rejecting an old version
  prevents one save from silently overwriting another.
- **What makes PATCH atomic?** No `await` occurs between checking the version and replacing
  validated state in this one-process event loop. Multiple processes need database transactions.
- **Why derive counters?** Independently incremented counters can drift from item states.
- **Why count needs-review as processed?** Extraction ended; human review has a separate lifecycle.
- **Why keep a local draft?** Replacing inputs on every poll would erase mid-edit text.
- **Why client components?** Ticket selection, polling, and editable drafts need browser
  state and effects. The server route resolves the job ID; FastAPI still owns extraction.
- **Why an API rewrite?** Browser requests stay on the frontend origin while Next.js
  forwards them to FastAPI. The same HTTP contract works in dev and production.
- **What disappears on restart?** Jobs, corrections, approvals, and versions; only the source reloads.
- **Why no queue service/database?** The brief permits in-memory state. Durable production
  jobs would need persistence and different scheduling infrastructure.

Run the tests and read their assertions. In a temporary experiment, remove a version
check, semaphore acquisition, validation call, or draft-protection condition and explain
the broken behavior before restoring it. Do not submit those experiments.
