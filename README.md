# Extraction Workbench

Extraction Workbench turns customer support tickets into structured proposals that
a reviewer can inspect, correct, approve, and export. Uncertainty and validation
failures stay visible so the reviewer retains the final decision.

The default mock provider uses deterministic text rules and runs locally without
an API key. The Gemini provider uses an LLM for extraction and classification.
Both providers share the same validation and retry pipeline.

## Stack and scope

The backend uses Python/FastAPI/Pydantic; the frontend uses Next.js App Router,
React, and TypeScript. State is stored in memory, and the two processes communicate over HTTP.
The application needs no database, Docker, or global CLI.

Repository layout: `backend/` contains the API, providers, and tests; `frontend/`
contains the App Router UI and tests; `data/` contains the original tickets. Local
keys, dependencies, build output, and caches are ignored.

The original brief is in [ASSIGNMENT.md](ASSIGNMENT.md). The frontend uses its required
Next.js App Router, with `/` and `/jobs/[id]` routes and a shared root layout.
The technical and product reasoning is documented in [DECISIONS.md](DECISIONS.md).

## Prerequisites

- Git to clone the repository.
- Python 3.12 or newer with pip and venv.
- Node.js 22.12 or newer with npm.
- Internet access for initial dependency installation.

Development was verified on Windows with Python 3.14.7 and Node.js 24.20.0. Mock mode
needs no network connection after installation. Direct dependencies are pinned and
the frontend lockfile is committed.

## Installation and startup

```sh
git clone https://github.com/Kushagra-Kataria/oraczen-extraction-workbench.git
cd oraczen-extraction-workbench
```

The application runs as two services. The following commands start each service
from a separate terminal in the repository root.

### Terminal 1: backend, Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The commands require no environment activation or PowerShell execution-policy changes.
The equivalent backend commands for macOS/Linux are:

```sh
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2: frontend, Windows PowerShell

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

On macOS/Linux, the command is `npm` rather than `npm.cmd`. On Windows, `npm.cmd`
avoids PowerShell's restriction on the `npm.ps1` wrapper.

The workbench is available at **http://127.0.0.1:5173**. Backend API docs are at
**http://127.0.0.1:8000/docs**; health is at **http://127.0.0.1:8000/api/health**.
Both services stay running during use; Ctrl+C stops each server.

The backend runs with one worker because multiple workers have separate in-memory state.
`--reload` can help development, but every restart clears jobs and edits.

## Configuration

The defaults work without an `.env` file. Custom configuration is loaded
from `backend/.env` after a backend restart. This command creates that file from the template:

```powershell
Copy-Item .env.example backend/.env
```

On macOS/Linux: `cp .env.example backend/.env`. A root `.env` remains supported for
existing setups, but `backend/.env` takes precedence when both files exist.

| Variable | Default | Purpose |
| --- | --- | --- |
| `EXTRACTION_PROVIDER` | `mock` | `mock` or optional `gemini` |
| `MAX_CONCURRENCY` | `4` | Shared provider cap across all jobs, range 1–20 |
| `MOCK_DELAY_MS` | `650` | Delay per mock attempt; `0` for fast processing |
| `PROVIDER_TIMEOUT_SECONDS` | `30` | Per-attempt timeout |
| `TICKETS_PATH` | `data/tickets.jsonl` | Path relative to repo root or absolute |
| `GEMINI_API_KEY` | empty | Server-only key required only in Gemini mode |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Optional real model identifier |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Next.js API rewrite target for development and production |

The browser always calls `/api`. The backend address is configured through `BACKEND_URL` in
the frontend process, `frontend/.env.local`, or the root `.env` before starting/building
Next.js. Backend-only settings stay in `backend/.env`. API rewrites are recorded at
build time; changing the production backend target requires a rebuild.

### Switching providers

Set the provider in `backend/.env`. For local deterministic processing without an API key:

```dotenv
EXTRACTION_PROVIDER=mock
```

For LLM extraction and classification with Gemini:

```dotenv
EXTRACTION_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
```

Restart the backend after changing providers, then start a new job. Restarting clears
existing jobs and edits because state is stored in memory.

In Gemini mode, selected tickets are sent to Google's Gemini API. Available quota depends on
the account; concurrency limiting is not requests-per-minute limiting.
Provider errors fail individual items without aborting the job.
Keys stay on the backend, outside `NEXT_PUBLIC_` variables and version control; `.env` is ignored.

## Deployed workbench

A deployed version is available at [oraczen-extraction-workbench.vercel.app](https://oraczen-extraction-workbench.vercel.app/).
It can be used to test the Gemini-backed extraction and classification workflow. Gemini
mode in a deployed environment requires `EXTRACTION_PROVIDER=gemini` and a server-only
`GEMINI_API_KEY` configured in that environment.

The adapter follows the [Gemini REST API](https://ai.google.dev/api/generate-content).
Its request shape and repair path are tested with a simulated HTTP transport.
Live Gemini 3.1 Flash-Lite was verified on 4 October 2026 using invented tickets:
outage/billing extraction, USD refund extraction, validation, corrections, approval,
stale-edit protection, and reviewed CSV export passed. This checks integration,
not accuracy across the assignment dataset.

A separate ten-ticket comparison found semantic errors despite valid output types:
mock misclassified a confidentiality footer, and Gemini inferred a refund that was
not requested. The mock footer defect is addressed by the text processing described
below; the Gemini refund error remains unresolved. The comparison does not establish
extraction accuracy, and all proposals still require approval before export.

The optional live check is reproducible from `backend` with:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_gemini.py
```

On macOS/Linux: `.venv/bin/python scripts/smoke_gemini.py`. The script requires a configured
Gemini key and consumes API quota. It creates an isolated app with invented tickets
in a temporary directory; it does not send the assignment dataset or change jobs in
the running workbench. Normal automated tests ignore local `.env` and provider
environment settings and remain offline.

## Usage

The review workflow has seven steps:

1. The inbox supports search, channel filters, individual selection, and
   **Select all 150 tickets**. **View ticket** shows the full original conversation
   and metadata; **Close** or Escape dismisses it without changing the selection.
2. **Extract** starts the selected batch.
3. Progress and available results remain visible while the batch is running.
4. Original text appears beside proposed fields. Focusing a field highlights its
   evidence quote when it is present in the body.
5. Fields are editable inline. **Save changes** validates supplied values and keeps a partial
   draft if other required fields remain missing.
6. **Approve & save** validates the complete record and records a human review.
   Invalid approval shows errors beside the relevant fields.
7. **Export reviewed** downloads approved, schema-valid records.

Edited fields are visibly marked human-edited. Approval is a reviewer decision, not
proof that every inference is correct. The mock deliberately returns invalid
severity once for `tkt_0005` and an invalid product twice for `tkt_0003`; these exercise
the repair and review paths through the same pipeline used by Gemini.

The queue sorts `needs_review` first and provides filters for human-edited, reviewed, and failed
records. Unsaved input survives polling. Switching records/filters requires save or
discard. Browser reload/close warns on an unsaved draft. Drafts are not durable across
leaving the page. Original extraction notes remain visible after corrections.

**Cancel job** stops queued/running work and keeps completed records. Unfinished items
become failed with cancellation notes; the job becomes `cancelled`.

## Architecture and contracts

The mock separates issue text from email boilerplate while retaining signatures
and quoted context. Its conservative rules favor specific issue phrases over broad
keywords and keep quoted unresolved issues available as context.

```text
Next.js App Router → HTTP /api rewrite → FastAPI → tracked job → shared semaphore
                                                            → mock/Gemini provider
                                                    → Pydantic validation
                                                    → retry once with errors
                                                    → in-memory review record
Human edit → field validation + complete validation → provenance + approval
CSV export → approved, schema-valid records only
```

The input is 150 UTF-8 JSONL objects, not a JSON array. Fields are `id`, `subject`,
`body`, `channel`, `received_at`, `from_email`, and an attachment count. The startup
loader rejects malformed records and duplicate IDs. Original data is never rewritten.

The business schema has eight fields: `company`, `product`, `category`, `severity`,
`requested_action`, `refund_amount`, `deadline`, and `escalated`. Only amount/deadline
are optional. Amounts are finite nonnegative numbers, dates are `YYYY-MM-DD`, and
booleans cannot be strings/numbers. Unknown fields and enum values are rejected.

A separate review record holds individually valid partial values without weakening
the business schema. It includes per-field source (`model`, `human`, `missing`),
grounding (`grounded`, `inferred`, `missing`), evidence, raw attempts, current errors,
original notes, and a version. `grounded` means a quote exists in the ticket, not
calibrated confidence or semantic proof.

A record is **Done** only when a provider output passes the complete Pydantic schema
on the first or second attempt. Missing optional amounts/dates are allowed; malformed
optional values are not. `escalated: false` and `requested_action: none` are valid values.
Missing quotes, inferred values, and ambiguity notes stay visible without forcing
an otherwise valid output into review.

Every output that fails validation twice becomes **Needs review**, including invalid
optional values, unknown fields, malformed JSON, and invalid proposal envelopes.
Both raw attempts, final validation errors, and individually valid draft fields remain
available. Invalid draft values are left empty for editing; sanitizing them never
automatically accepts a rejected output. `schema_valid` remains false until a human
save/approval validates the draft. A reviewer can repair a value or explicitly approve
a valid draft with an empty optional field. Provider connection/timeouts remain **Failed**.
**Done** is separate from approval, which still gates CSV export.

```text
queued + running + done + failed = total
done includes needs_review; needs_review is also reported as a subset
job flips to done after every item is terminal
```

Job completion describes processing, not approval. Human corrections can change the
needs-review/failed subset without restarting the job.

## HTTP API

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/health` | Health and selected provider |
| GET | `/api/tickets` | Original dataset |
| POST | `/api/jobs` | `{"ticket_ids":["tkt_0003","tkt_0005"]}` → `202` job snapshot |
| GET | `/api/jobs/{id}` | State, counters, per-item status |
| GET | `/api/jobs/{id}/results` | Available records with source text |
| POST | `/api/jobs/{id}/cancel` | Cancel outstanding work |
| PATCH | `/api/records/{id}` | Versioned corrections and optional approval |
| GET | `/api/jobs/{id}/export.csv` | Reviewed CSV attachment |

Example correction body, using the current version:

```json
{
  "version": 1,
  "fields": { "product": "Zen Vault", "severity": "low" },
  "reviewed": true
}
```

`422` reports field errors. `409` rejects a stale version. Invalid corrections are
atomic: none of the changes apply. Later edits clear approval unless approval is
explicitly requested again in the same call.

CSV headers are `ticket_id`, the eight fields in schema order, and `human_edited_fields`
(semicolon-separated). Missing optional values are blank, dates are ISO, booleans
lowercase. The CSV writer handles commas, quotes, and newlines. Formula-like text is
prefixed with an apostrophe for spreadsheet safety. No approvals means headers only.

## Tests and build

From `backend/`, Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check app tests
.\.venv\Scripts\ruff.exe format --check app tests
```

On macOS/Linux, use `.venv/bin/python` and `.venv/bin/ruff`.
From `frontend/`, Windows (use `npm` on macOS/Linux):

```powershell
npm.cmd test
npm.cmd run format:check
npm.cmd run build
```

Backend coverage includes retry feedback, malformed JSON, repeated failure without
job failure, progress transitions, global concurrency, HTTP 202 responsiveness,
cancellation, all 150 tickets, corrections, stale versions, CSV, timeouts, and the
simulated Gemini transport. Frontend tests cover selection, early results, field
errors, provenance, numeric payloads, inbox previews, and protecting drafts during polling/switching.

The production frontend runs with `npm.cmd run start` after building, with the dev
server stopped and FastAPI running. Both development and production use port
5173 and forward `/api` to FastAPI. Next.js handles direct visits to `/jobs/[id]` and
unknown-page responses without a separate SPA fallback configuration.

## Troubleshooting and limitations

- Cannot reach backend: start FastAPI, check `/api/health` and `BACKEND_URL`.
- Port in use: stop the existing process or update the ports/proxy.
- Job missing after restart: state was lost; return to the inbox and start a new job.
- Empty export: approve a complete, valid record first.
- Many review flags: missing facts are deliberately not guessed into validity.
- Gemini errors: check key/quota; mock mode remains available without a key.

Database storage, authentication, a durable audit, and RPM limiting are outside this
implementation. Backend restarts lose jobs and edits. [DECISIONS.md](DECISIONS.md)
records the trade-offs.
