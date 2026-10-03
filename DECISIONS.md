# Technical and product decisions

## Data observations

Twenty tickets were inspected before schema design. The dataset has 150 unique IDs,
45 email/42 chat/34 web form/29 phone transcript channel labels; labels do not reliably
describe body format. Twenty-five tickets count attachments without providing their
contents. Signatures, footers, forwarded replies, typos, and sender/company conflicts
affect extraction. Some arrival dates precede events in the text; relative dates cannot
be safely resolved against arrival time. The original source stays intact.

## Five required product choices

1. **Missing severity:** leave it unresolved and request review. Guessing can hide an
   urgent issue or over-prioritize a minor one. Required nulls fail the strict business
   schema; a separate draft retains valid individual fields. Explicit impact can
   produce a severity proposal with its source quote.
2. **French/EUR (`tkt_0058`):** keep the EUR amount in a warning, leaving the USD refund
   empty. Two invoices also need reconciliation; no exchange rate or total refund is
   assumed. Prefer the body company, flagging its conflict with the sender domain.
3. **Multiple issues (`tkt_0089`):** select `churn_risk` for the non-renewal threat. Keep
   export, billing, and SSO problems in notes. The two USD amounts are not an explicit
   refund request. A single category necessarily loses detail.
4. **`please advise` / `?`:** skip provider calls and create incomplete drafts. Tokens
   cannot recover absent facts; customer clarification is the right next step.
5. **Polling:** get progress then available results about every second while running.
   Sequential requests ensure a terminal snapshot includes the last result. Stop at
   completion/cancellation and abort on unmount. This costs two requests per interval
   and roughly a second of latency but keeps stream lifecycle complexity out of the
   timeboxed app. Request errors expose manual retry.

## Architecture and LLM selection

FastAPI/Pydantic express the business contract. Strong task references support orderly
shutdown and cancellation; one shared semaphore caps concurrency across jobs.
Counters derive from items. Twice-invalid proposals count as processed/needs-review;
provider errors count as failed. Both are terminal, so one bad item never blocks a batch.
Cancellation counts unfinished items failed with explicit notes and cancelled job state.

The deterministic mock is the grading default. Conservative text rules demonstrate
the workflow, not LLM accuracy. Body evidence takes priority over misleading subjects;
agent suggestions in a transcript do not override the caller's answer. `tkt_0005`
repairs on retry and `tkt_0003` deliberately fails twice. Missing facts can cause other
tickets to remain invalid too.

Optional Gemini 3.1 Flash-Lite was chosen for structured extraction and its documented
free tier. Model availability/quota depend on the account; the model is configurable.
The adapter sends source instructions and a JSON schema. Remote proposals permit
nulls while the local Pydantic contract stays authoritative. Transport tests verify
request shape and shared retries. On 4 October 2026, a live check with invented
outage/billing tickets verified extraction, USD refund parsing, validation, corrections,
approval, stale-edit protection, and CSV export. Assignment tickets were not sent in
that check; semantic accuracy on those 150 tickets remains unevaluated.
References: [model](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite),
[pricing](https://ai.google.dev/gemini-api/docs/pricing),
[REST API](https://ai.google.dev/api/generate-content).

React/Vite/TypeScript was explicitly requested by the owner. It departs from the brief's
Next.js App Router requirement; documentation does not make this compliant. React
Router preserves `/` and `/jobs/:id`. The local Vite proxy keeps requests same-origin.
Plain CSS and system font fallbacks avoid an external font/component dependency.

## Review and trade-offs

Grounding flags replace arbitrary confidence percentages. Exact quotes are checked
against the source, but quote existence does not prove semantic correctness.
Human-edited fields have explicit provenance; whole-record approval is separate.
Original attempts and current field provenance are retained, not a full edit-event audit.

PATCH reuses the extraction field annotations, validates before replacing state, and
requires complete validity for approval. A version rejects stale writes. Partial repairs
can be saved. Later edits reset approval unless explicitly re-approved. The UI preserves
drafts during polling and asks before switching records/filters.

In-memory storage meets the brief and limits setup to two processes. Restarting loses
jobs, approvals, edits, and versions. Multiple workers would disagree; one is required.
Concurrency limiting does not enforce RPM quota; quota errors fail individual items.
CSV uses the standard library and escapes spreadsheet formulas.

## Verification and another day

Tests cover the three required backend scenarios plus all 150 tickets, timeouts,
cancellation, corrections, stale edits, CSV, and simulated Gemini calls. Frontend tests
cover selection, incremental results, field errors, provenance, and draft protection.
Browser checks exercise demo processing, correction, approval, and CSV download.
Setup is checked in a fresh local clone.

Another day would add SQLite and an edit-event audit, labeled accuracy evaluation,
a provider RPM limiter/backoff and broader date/currency handling. The opt-in live
Gemini smoke script uses only invented data; labeled assignment accuracy checks remain
future work.
Keyboard shortcuts and single-record reruns are deferred. The mock's narrow phrase
rules and quote-only grounding are the weakest parts: they establish workflow behavior,
not semantic accuracy. Drafts are not durable; internal navigation away from the job
page can discard them despite record-switch/reload guards. The Vite departure remains
a submission risk.
