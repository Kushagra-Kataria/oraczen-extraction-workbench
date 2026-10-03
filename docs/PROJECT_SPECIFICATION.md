# Extraction Workbench - Project Specification

Snapshot: 3 October 2026, code commit d0b3567.

ORACZEN / TAKE-HOME B

Extraction<br/>Workbench

Complete project specification

A full-stack workspace for turning customer support conversations into validated records that a person can inspect, correct, approve, and export.

| Input | Business fields | Current checks |
| --- | --- | --- |
| 150 source tickets | 8 structured values | 30 backend + 8 frontend tests |

### Implementation snapshot - 3 October 2026
The backend and frontend are implemented. The running app uses the deterministic mock provider. An optional Gemini adapter is implemented and tested with simulated HTTP responses; a live Gemini call has not been verified. This document describes code snapshot <b>d0b3567</b> and distinguishes completed work from future additions.

Submission: Sunday, 4 October 2026, 12:00 PM IST. Deliver a public GitHub repository containing source code, README.md, DECISIONS.md, .env.example, and a clear history of real development commits.

Repository: <link href="https://github.com/Kushagra-Kataria/oraczen-extraction-workbench" color="#137F76">Kushagra-Kataria/oraczen-extraction-workbench</link>

### Reading map

| Page | Topic |
| --- | --- |
| 2 | Product scope and feature inventory |
| 3 | Ticket data and extraction schema |
| 4-5 | Pipeline, classification, uncertainty, and failure handling |
| 6-7 | Human review, CSV, architecture, and API contracts |
| 8-10 | Setup, verification, delivery, limitations, and next steps |

PROJECT SPECIFICATION / 02

## What the product does

Primary user: a support reviewer responsible for the final structured record.

The workbench provides one workflow: load tickets, select a batch, extract proposals, review uncertain results, save corrections, approve valid records, and export them. It processes the supplied dataset; it is not a help-desk system for receiving new customer messages.

| Capability | Implemented behavior |
| --- | --- |
| Ticket inbox | Lists all 150 tickets with subject, body preview, channel, date, and source ID. |
| Search and selection | Searches ID, subject, body, and sender. Filter by channel; select a subset, filtered rows, or the complete dataset. Selection survives filters. |
| Background extraction | Starts a job immediately, caps simultaneous provider calls, and processes tickets independently. |
| Live progress | Shows queued/running/processed/failed counters and per-item state. Results appear as items finish, before the whole batch ends. |
| Validation and retry | Validates JSON and all business fields. One repair attempt receives actual validation errors. Invalid drafts keep raw attempts. |
| Review workspace | Displays original text and editable proposals together, field evidence, missing/inferred markers, warnings, and field-specific errors. |
| Corrections and approval | Validated partial edits, human provenance, stale-version protection, and explicit whole-record approval. |
| Queue and export | Needs-review sorting; filters for human-edited, reviewed, and failed records. One-click CSV exports approved, valid records. |
| Cancel and draft guards | Cancels unfinished work while retaining results; polling preserves unsaved edits, and record switches require save/discard. |

### Three separate concepts

Review demo: an eight-ticket selection shortcut highlighting difficult cases. Mock provider: the local extraction engine used for all selected tickets, required for no-key grading. Gemini provider: an optional real LLM used when configured. Selecting all tickets does not switch the provider.

PROJECT SPECIFICATION / 03

## Data and business contract

The original source is data/tickets.jsonl: UTF-8 JSON Lines, not a JSON array.

Each of the 150 lines contains one ticket. Input fields are id, subject, body, channel, received_at, from_email, and attachments. Startup rejects malformed records or duplicate IDs. The app reads the source without rewriting it. Attachments are counts only; their contents are unavailable.

| Field | Required? | Type and accepted values |
| --- | --- | --- |
| company | Yes | Nonblank string; trimmed; maximum 200 characters. |
| product | Yes | Zen Orchestrator \| Zen Studio \| Zen Connect \| Zen Insights \| Zen Vault |
| category | Yes | outage \| billing \| bug \| feature_request \| how_to \| churn_risk |
| severity | Yes | low \| medium \| high \| critical |
| requested_action | Yes | refund \| credit \| fix \| callback \| information \| none |
| refund_amount | No | Finite, nonnegative JSON number in USD; null when unresolved or absent. |
| deadline | No | Valid calendar date in YYYY-MM-DD format; null when unresolved or absent. |
| escalated | Yes | Actual JSON boolean: true or false. Strings/numbers are rejected. |

### Review metadata is separate from the business schema

Each result also stores record/job/ticket IDs, status, schema validity, approval, attempt count, raw outputs, current errors, original notes, version, and per-field source/grounding/evidence. A partial draft can hold null required values for editing; the strict business model still rejects those values until they are repaired.

### Observed source complexity

Channels: 45 email, 42 chat, 34 web_form, and 29 phone_transcript. Twenty-five tickets count attachments. Bodies include quoted replies, signatures, legal footers, French text, typos, sparse content, relative dates, and spoken amounts. Sender domains and body companies can conflict; channel labels do not reliably describe body format.

PROJECT SPECIFICATION / 04

## How extraction runs

The same scheduling, validation, retry, and review pipeline serves both providers.

Select -> schedule -> provider -> validate -> store -> human review -> CSV.

| Step | System behavior |
| --- | --- |
| 1. Validate request | Accept 1-150 ticket IDs. Reject unknown IDs and duplicates with HTTP 422. |
| 2. Start a job | POST /api/jobs returns HTTP 202 with the job ID before extraction completes. |
| 3. Bound concurrency | Tracked asynchronous tasks share one semaphore across jobs. Default cap: four provider calls. |
| 4. Skip sparse input | Bodies exactly '?' or 'please advise' create incomplete review drafts without provider calls. |
| 5. Validate output | Check the proposal envelope, each business field, and exact source-quote matches. |
| 6. Retry or finalize | After invalid output, retry once with actual field errors. Second failure retains partial values/raw JSON and becomes needs_review. |
| 7. Isolate failures | Per-attempt timeout or provider exceptions fail one item; other tickets continue. |

### Completion and approval are different

A job is done when all items have reached a terminal state. An item marked done has a complete proposal without a review-triggering issue under the current policy; it is not automatically approved for CSV. Needs-review items also count as processed. A person must approve every record intended for export.

```text
queued + running + done + failed = total
done includes needs_review; needs_review is a reported subset
```

PROJECT SPECIFICATION / 05

## Extraction and classification rules

Current mock behavior is conservative text matching; it is not an LLM accuracy benchmark.

The mock removes quoted reply lines before most classification. It finds product names and company signatures; a sender-domain fallback is visibly inferred. Categories use ordered phrase rules, preferring the body over the subject: churn risk, billing, outage, feature request, bug, then how-to. This prioritization resolves one category from a schema that cannot represent several issues.

Severity uses explicit phrases such as urgent, critical, scheduled-job failure, blocker, and workaround. Otherwise it remains missing. Requested actions use refund, credit, call, fix, and information cues; agent lines in phone transcripts are excluded so agent suggestions do not override the caller. Refunds require an exact sole USD amount; only explicit ISO deadlines are extracted. Escalation uses escalation or leadership cues.

| Case | Chosen behavior |
| --- | --- |
| Missing severity | Do not invent impact. Leave it missing and require review, even after the repair attempt. |
| French + EUR (0058) | Keep the original EUR amount in notes, leave USD refund empty, and flag the sender/company conflict. |
| Multiple issues (0089) | Choose churn_risk for the renewal threat; preserve other problems in notes. Ambiguous dates and amounts remain unresolved. |
| Typos (0105) | Normalize 'zen studioo' to Zen Studio with a visible warning; missing severity still needs review. |
| Spoken amount (0131) | Classify the caller's accepted action as credit; do not fabricate an exact amount from 'nine thousand something'. |
| Deliberate mock failures | 0005 returns invalid severity on attempt one and repairs it. 0003 returns an invalid product on both attempts. |

### Why some results require review
Missing required facts, unsupported positive values, conflicts, normalization, currency/amount ambiguity, relative deadlines, and multi-issue notes trigger review. Safe defaults action=none and escalated=false remain labelled inferred without forcing review. Routine attachment notes are informational. Quote matching proves a phrase exists, not that its interpretation is correct.

Gemini receives the same source, instructions, JSON schema, and repair feedback. Remote proposals may contain nulls; local Pydantic validation remains authoritative. The current review-note trigger uses known text prefixes, so arbitrary LLM wording may miss an optional ambiguity; structured warning codes are a future improvement.

PROJECT SPECIFICATION / 06

## Human review and final export

A reviewer owns the final decision; schema validity and provenance remain visible.

| Reviewer action | Result |
| --- | --- |
| Select a record | Raw source and proposal stay on one page. Desktop uses side-by-side panels; smaller screens stack them. |
| Focus a field | Its exact evidence quote is highlighted when present in the body; missing/inferred/human-edited indicators remain visible. |
| Inspect a failure | View per-field errors, original notes, and raw provider attempts without losing the salvageable draft. |
| Save changes | Submit only changed fields. Valid partial repairs can be saved while unrelated required fields remain missing. |
| Approve and save | Validate the entire record. Reject invalid approval with field-specific errors; valid approval makes the record export-eligible. |
| Edit an approved record | Mark supplied fields as human-edited. Clear previous approval unless approval is explicitly requested again. |
| Save an old version | HTTP 409 prevents silent overwrite of a newer record. Refresh and reconcile the draft. |
| Switch or cancel | Unsaved edits require save/discard before record switching. Cancellation retains completed records and fails unfinished items with notes. |

### CSV contract

The export contains only reviewed=true and schema_valid=true records. Headers are ticket_id, company, product, category, severity, requested_action, refund_amount, deadline, escalated, and human_edited_fields. Human-edited field names are separated by semicolons. Missing optional values are blank, dates are ISO, booleans lowercase, and standard CSV quoting preserves commas, quotes, and newlines. Formula-like text is prefixed with an apostrophe. With no approvals, the file contains headers only.

### State protection and limits

Polling does not replace a dirty local draft; older responses cannot overwrite a newer save. Browser reload/close warns on dirty input. Internal navigation away from the job page can still discard a draft. Original attempts and current human field provenance are retained, but a durable history of every edit is not implemented.

PROJECT SPECIFICATION / 07

## Architecture and API

Two local services communicate over HTTP. One backend worker owns process-local state.

| Layer / source | Responsibility |
| --- | --- |
| frontend/ - React, Vite, TypeScript | React Router pages, selection, polling, local drafts, evidence display, correction controls, responsive CSS. |
| backend/app/routes.py | FastAPI HTTP boundaries, ID checks, status/results, corrections, cancellation, and reviewed CSV. |
| schemas.py + review.py | Strict Pydantic contracts, partial-field validation, versions, approval, and provenance. |
| jobs.py + store.py | Tracked tasks, global semaphore, counter arithmetic, cancellation, and in-memory dictionaries. |
| extraction.py + providers/ | Shared validation/retry/grounding pipeline; interchangeable mock and Gemini adapters. |
| config.py + tickets.py | Root .env settings, secret handling, stable paths, and JSONL loading. |

| Method and route | Request / response purpose |
| --- | --- |
| GET /api/health | Health and selected provider. |
| GET /api/tickets | Original ticket list. |
| POST /api/jobs | {ticket_ids: [...]} -> HTTP 202 job snapshot. |
| GET /api/jobs/{id} | Job state, queued/running/done/failed counts, and per-item state. |
| GET /api/jobs/{id}/results | Available records, metadata, and original tickets. |
| POST /api/jobs/{id}/cancel | Stop unfinished work; return updated status. |
| PATCH /api/records/{id} | {version, fields, reviewed?}; validated correction or 422/409. |
| GET /api/jobs/{id}/export.csv | CSV attachment containing reviewed, valid records. |

Development and preview requests use Vite's /api proxy. Job-page polling reads progress then results approximately once per second, stops at terminal state, and aborts on unmount. Production hosting would need an API reverse proxy and SPA fallback for /jobs/:id. Cloud deployment is not part of the current implementation.

PROJECT SPECIFICATION / 08

## Installation and provider setup

Requirements: Git, Python 3.12+, Node.js 22.12+, npm, and network access for package installation.

Clone the public repository and open two terminals at its root. Defaults work without a .env file. The commands below are for Windows PowerShell; macOS/Linux uses python3, .venv/bin/python, and npm.

### Terminal 1 - backend

```text
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2 - frontend

```text
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs. Keep both processes running; use Ctrl+C to stop. Run exactly one backend worker.

| Root .env variable | Default / purpose |
| --- | --- |
| EXTRACTION_PROVIDER | mock; select gemini for real hosted LLM calls. |
| GEMINI_API_KEY | Empty; a personal server-only key is required in Gemini mode. |
| GEMINI_MODEL | gemini-3.1-flash-lite; configurable model identifier. |
| MAX_CONCURRENCY | 4; cap 1-20 simultaneous provider calls across jobs. |
| MOCK_DELAY_MS | 650; artificial delay per attempt, 0-10000 ms. |
| PROVIDER_TIMEOUT_SECONDS | 30; per-attempt timeout, greater than 0 and at most 120. |
| TICKETS_PATH | data/tickets.jsonl; root-relative or absolute dataset path. |
| BACKEND_URL | http://127.0.0.1:8000; Vite development/preview proxy target. |
| VITE_API_BASE_URL | /api; browser API prefix. Never put a secret in a VITE_ variable. |

For Gemini: copy .env.example to root .env, set provider=gemini and your key, then restart services. Selected tickets are sent to Google's API. Account/model availability and quota require live verification; a concurrency cap does not enforce requests-per-minute limits. No real key is included or committed.

PROJECT SPECIFICATION / 09

## Verification and acceptance criteria

Checks demonstrate workflow behavior; they do not establish real-model extraction accuracy.

| Evidence | Observed result / scope |
| --- | --- |
| Backend suite | 30 passing tests after the review-default fix: validation, retry feedback, job completion, progress, concurrency, cancellation, timeout, correction, versions, CSV, and simulated Gemini transport. |
| Frontend suite | 8 passing tests after full-source selection was added: filtering, batch submission, incremental results, field errors, provenance, payload types, and draft protection. |
| Static checks | Ruff lint/format checks passed; frontend Prettier, TypeScript checking, and production build passed for their latest relevant changes. |
| Live full batch | 150/150 terminal results, 0 provider failures: 13 done and 137 needs_review under current mock rules. Those numbers describe routing, not accuracy or approvals. |
| Browser workflow | Ticket selection, early results, correction, invalid approval feedback, provenance, approval, actual CSV download, and responsive layout checked. |
| Clean-clone installation | Snapshot 7b2ba81 installed and ran from a fresh local clone without copied .env or packages; 29 backend / 7 frontend tests then passed. Later changes were verified in the working checkout. |

### Assignment acceptance checklist

The grader can start the app without a key, select any ticket subset, receive HTTP 202 immediately, watch bounded concurrent processing, and inspect early results. Malformed output triggers one repair; repeated failure leaves a reviewable draft without failing the job. Human edits are validated and distinguishable, and only approved valid records export. Required decision notes and setup instructions are present. Frontend framework compliance remains an exception described on page 10.

### How to reproduce checks

```text
# From backend/
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check app tests
# From frontend/
npm.cmd test
npm.cmd run format:check
npm.cmd run build
```

PROJECT SPECIFICATION / 10

## Delivery, limitations, and next work

The assignment deliverable is the repository; this PDF is a companion specification.

| Deliverable | Where / purpose |
| --- | --- |
| Source code | backend/ and frontend/; original data/tickets.jsonl preserved. |
| README.md | Prerequisites, installation, architecture, usage, API, tests, configuration, and troubleshooting. |
| DECISIONS.md | Five required product decisions, data observations, provider choice, trade-offs, and another-day improvements. |
| .env.example | All configurable values, empty key placeholders, no sensitive credentials. |
| Git history | Small real development commits; no fabricated dates or reconstructed history. Snapshot d0b3567 contains 15 commits. |
| Interview preparation | docs/INTERVIEW_GUIDE.md explains reading order, ticket lifecycle, async tasks, versions, and failure behavior. |

### Known requirement departure
The original brief specifies Next.js with the App Router. The owner requested React with Vite, which is the implemented frontend. That choice is documented but does not make the project compliant with the Next.js requirement. Resolve this with the assignment reviewer or migrate the frontend before submission.

### Current limits

The mock uses narrow text rules and leaves many missing facts unresolved. Real Gemini calls have not been verified. In-memory jobs, edits, approvals, and versions disappear on backend restart; multiple workers would disagree. There is no database, authentication, durable audit log, provider RPM limiter, or semantic accuracy evaluation. Attachment contents are unavailable. Note-based review triggers depend on known phrases. Internal navigation can discard drafts.

### Implementation priorities after this snapshot

First, verify Gemini with a locally stored key and a small labeled ticket sample. Then add structured warning codes, rate-limit backoff, persistence and edit-event history, and evaluation against human labels. Keyboard-first review, single-record reruns, richer currency/date handling, Docker Compose, and streaming progress are deferred. Persistent multi-user production deployment needs additional design.

### Submission and interview preparation

Recheck a fresh clone of the final revision, confirm public repository access, and send the URL before 4 October 2026 at 12:00 PM IST. Read the implementation before submitting: explain one ticket from input to CSV, why missing facts require review, and what breaks when validation, the semaphore, or version checks are removed.

Source of this specification: ASSIGNMENT.md, DATA.md, README.md, DECISIONS.md, backend/app modules, frontend/src modules, automated test results, and recorded local/browser verification. Provider API reference: <link href="https://ai.google.dev/api/generate-content" color="#137F76">ai.google.dev/api/generate-content</link>.
