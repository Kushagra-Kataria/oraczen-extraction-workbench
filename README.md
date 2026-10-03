# Extraction Workbench

A human review tool that extracts structured proposals from customer support tickets,
shows uncertainty and validation failures, and supports corrections before CSV export.

**Runs without an API key.** The default provider is a deterministic text-based mock.
An optional Gemini adapter uses the same validation and retry pipeline.

## Stack and scope

Python/FastAPI/Pydantic backend, React/Vite/TypeScript frontend, and process-local storage.
Two processes communicate over HTTP. No database, Docker, or global CLI is needed.

The original brief is in [ASSIGNMENT.md](ASSIGNMENT.md). It requires Next.js App Router.
React/Vite was explicitly requested for this project and departs from that requirement;
documenting the choice does not make it compliant. Other required workflows are implemented.
See [DECISIONS.md](DECISIONS.md) for technical and product choices.

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

Open two terminals in the repository root.

### Terminal 1: backend, Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

No environment activation or PowerShell execution-policy changes are needed.
For macOS/Linux, use these backend commands instead:

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

On macOS/Linux, replace `npm.cmd` with `npm`. Using `npm.cmd` avoids PowerShell's
restriction on the `npm.ps1` wrapper.

Open **http://127.0.0.1:5173**. Backend API docs are at
**http://127.0.0.1:8000/docs**; health is at **http://127.0.0.1:8000/api/health**.
Keep both terminals running. Stop each server with Ctrl+C.

Run one backend worker. Multiple workers have separate in-memory state.
`--reload` can help development, but every restart clears jobs and edits.

## Configuration

Defaults work without an `.env` file. To customize them, copy `.env.example` to `.env`
**in the repository root**, edit it, and restart both services:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux: `cp .env.example .env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `EXTRACTION_PROVIDER` | `mock` | `mock` or optional `gemini` |
| `MAX_CONCURRENCY` | `4` | Shared provider cap across all jobs, range 1–20 |
| `MOCK_DELAY_MS` | `650` | Delay per mock attempt; `0` for fast processing |
| `PROVIDER_TIMEOUT_SECONDS` | `30` | Per-attempt timeout |
| `TICKETS_PATH` | `data/tickets.jsonl` | Path relative to repo root or absolute |
| `GEMINI_API_KEY` | empty | Server-only key required only in Gemini mode |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Optional real model identifier |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Vite development/preview proxy target |
| `VITE_API_BASE_URL` | `/api` | Browser API prefix |

For real extraction, set `EXTRACTION_PROVIDER=gemini` and your own `GEMINI_API_KEY`.
Tickets are then sent to Google's Gemini API. Check your account's current free-tier
quota before a batch; concurrency limiting is not requests-per-minute limiting.
Provider errors fail individual items without aborting the job.
Never put a key in a `VITE_` variable or commit `.env`.

The adapter follows the [Gemini REST API](https://ai.google.dev/api/generate-content).
Its request shape and repair path are tested with a simulated HTTP transport.
**Live Gemini extraction has not been verified with a real key.** Mock mode is the
fully tested grading path.

## Usage and demo

1. Search/filter the inbox and select tickets. Selection persists across filters. Use
   **Select all 150 tickets** for a complete batch, or **Load review demo (8)** for the
   deliberately difficult examples.
2. Click **Extract** to start the selected batch.
3. Watch progress and open results while the batch is still running.
4. Compare the original text with proposed fields. Focusing a field highlights its
   evidence quote when it is present in the body.
5. Fix fields inline. **Save changes** validates supplied values and keeps a partial
   draft if other required fields remain missing.
6. **Approve & save** validates the complete record and records a human review.
   Invalid approval shows errors beside the relevant fields.
7. Click **Export reviewed** to download approved, schema-valid records.

| Ticket | Behavior in mock mode |
| --- | --- |
| `tkt_0005` | Deliberately invalid first severity, repaired on retry |
| `tkt_0003` | Deliberately invalid product twice; partial draft and raw outputs retained |
| `tkt_0004`, `tkt_0020` | Provider skipped because content is insufficient |
| `tkt_0058` | French text, EUR warning, sender/company conflict; no USD conversion |
| `tkt_0089` | Churn priority, other issues in notes, ambiguous deadline left empty |
| `tkt_0105` | Product typo normalized with a visible warning |
| `tkt_0131` | Caller accepts a credit; approximate spoken amount stays unresolved |

For a quick correction/export example, open `tkt_0003`, select **Zen Vault**, choose
severity after reviewing impact, then approve. Those edited fields are visibly marked
human-edited. Approval is a reviewer decision, not proof that every inference is correct.

The queue sorts `needs_review` first and filters human-edited, reviewed, and failed
records. Unsaved input survives polling. Switching records/filters asks you to save or
discard. Browser reload/close warns on an unsaved draft. Drafts are not durable across
leaving the page. Original extraction notes remain visible after corrections.

**Cancel job** stops queued/running work and keeps completed records. Unfinished items
become failed with cancellation notes; the job becomes `cancelled`.

## Architecture and contracts

```text
React/Vite → FastAPI → tracked job → shared semaphore → mock/Gemini provider
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

The review queue focuses on missing or ambiguous customer facts. A missing quote for
the safe defaults `requested_action: none` and `escalated: false` remains visibly
labelled as inferred but does not send an otherwise complete record to review. Routine
attachment metadata is informational; identity conflicts, currency/amount ambiguity,
typo normalization, relative dates, and multi-issue tickets still require review.

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
errors, provenance, numeric payloads, and protecting drafts during polling/switching.

To check the built frontend, stop its dev server and run `npm.cmd run preview` after
building, keeping FastAPI running. Preview uses the same proxy on port 5173.
External hosting needs SPA fallback for `/jobs/:id` and an API reverse proxy; Vite
preview is not a production deployment service.

## Troubleshooting and limitations

- Cannot reach backend: start FastAPI, check `/api/health` and `BACKEND_URL`.
- Port in use: stop the existing process or update the ports/proxy.
- Job missing after restart: state was lost; return to the inbox and start a new job.
- Empty export: approve a complete, valid record first.
- Many review flags: missing facts are deliberately not guessed into validity.
- Gemini errors: check key/quota; mock mode remains available without a key.

No database, authentication, durable audit, or RPM limiter is included. Backend
restarts lose jobs and edits. See [DECISIONS.md](DECISIONS.md) for trade-offs and
[docs/INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) for a code-reading walkthrough.
