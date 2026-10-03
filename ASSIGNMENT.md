# Take-home B: Extraction Workbench

## What this is

Customers send us support tickets as prose: email chains, chat logs, call transcripts,
occasionally a single word. Downstream systems need structured records. An LLM does the
first pass; a human reviews anything the model got wrong or was not confident about.

Build the tool that human uses.

You have 150 raw tickets in [data/tickets.jsonl](data/tickets.jsonl). Read fifteen or
twenty of them before you design anything. They include forwarded chains, email
signatures, legal footers, typos, a French one, a call transcript, and a ticket whose
entire body is `?`.

## Timebox and expectations

Budget around 8 hours of focused work, spread over up to 4 days. The "must build"
section done well beats everything half-done. If you run out of time, stop and write
what you would have done next in `DECISIONS.md`.

The hard part of this task is not the extraction. It is what your system does when the
extraction is wrong, and how it tells the user.

## Stack

- Backend in Python. FastAPI preferred; Flask or Django REST are acceptable.
- Frontend in Next.js with the App Router, TypeScript, and React.
- Two processes talking over HTTP.
- Styling is your call. We are not scoring visual polish, but a review tool that is
  painful to use has failed at its job.
- No database required. In-memory state that survives for the life of the process is
  fine. Note in `DECISIONS.md` what breaks when the process restarts.

## The record you are extracting

```bash
company            string, required
product            one of: Zen Orchestrator | Zen Studio | Zen Connect | Zen Insights | Zen Vault
category           one of: outage | billing | bug | feature_request | how_to | churn_risk
severity           one of: low | medium | high | critical
requested_action   one of: refund | credit | fix | callback | information | none
refund_amount      number, optional, in USD
deadline           date, optional
escalated          boolean
```

Define this as a Pydantic model and validate every model output against it. That
validation is the point of the exercise, not an afterthought.

## Must build

### Backend

`POST /api/jobs` takes a list of ticket ids, returns `202` with a job id, and starts
processing in the background. The request must not block until extraction finishes.

`GET /api/jobs/{id}` returns the job's state and its progress: how many items are
queued, running, done, and failed, plus per-item status.

`GET /api/jobs/{id}/results` returns the extracted records.

`PATCH /api/records/{id}` accepts a human correction to any field, validates it the
same way, and records that the value was human-edited rather than model-generated.
A reviewer looking at the record later must be able to tell which fields a person
touched.

`GET /api/jobs/{id}/export.csv` returns the reviewed records as CSV with correct
headers and content type.

Extraction rules:

- Process items concurrently, with a configurable cap. Firing 150 simultaneous
  requests at a model provider is not a design.
- If the model's output fails schema validation, retry once, feeding the validation
  error back in. If the second attempt also fails, mark the item `needs_review`,
  keep the raw output, and move on. One bad ticket must never fail the job.
- Every record carries a per-field confidence or a flag for fields the model was not
  able to ground in the ticket text. How you represent that is your call; the UI has
  to be able to surface it.

The whole thing must run with no API key configured. Ship a mock provider behind the
same interface, selected by an environment variable, that produces plausible records
from the ticket text, is deterministic for the same input, includes a small artificial
delay so progress is observable, and deliberately returns invalid output for a couple
of tickets so the retry and `needs_review` paths actually run. We will grade with the
mock. Using a real provider as well is welcome; use a free tier and never commit a key.

### Frontend

`/` lists the tickets with enough of each body visible to be recognisable, lets the
user filter and select a subset, and starts a job.

`/jobs/[id]` shows progress while the job runs, updating without a manual refresh, and
per-item state as each finishes. Do not make the user wait for the whole batch to see
the first result.

The results view puts the raw ticket next to the extracted fields so the reviewer can
check the model's work without switching pages. Fields are editable inline, with
validation errors shown against the field rather than as a generic failure. Items in
`needs_review` are visually distinct and sort to the top. Export is one click.

### Tests

At least three backend tests with real assertions:

- one that feeds malformed model output through the validator and asserts the retry
  happens
- one that asserts an item which fails twice lands in `needs_review` and the job still
  completes
- one that pins the progress arithmetic, including the moment the job flips to done

At least one frontend test, or a paragraph in `DECISIONS.md` on what you would test.

## Should build, if time allows

- Cancel a running job, and have the UI reflect it promptly.
- Keyboard-first review: move between records and fields without the mouse.
- A filter for "human-edited" records.
- Re-run extraction on a single record after editing the prompt or the model choice.

## Stretch, purely optional

- Optimistic updates on `PATCH` with rollback when the server rejects the edit.
- Server-sent events instead of polling, with a note on why.
- Docker Compose that brings both services up with one command.

## Things you have to decide yourself

Any defensible answer scores; an undocumented one does not. A sentence on each in
`DECISIONS.md`.

1. A ticket says nothing about severity. Does the model guess, does the field come back
   empty, or does the record go to `needs_review`? Justify it as a product decision,
   not a technical one.
2. Ticket `tkt_0058` is in French and mentions an amount in EUR. `refund_amount` is
   specified in USD. Decide what you do and make it visible to the reviewer.
3. Ticket `tkt_0089` contains three separate problems, two categories, and a renewal
   threat. Your schema allows one category. Decide how you handle multi-issue tickets.
4. Two tickets have bodies of `please advise` and `?`. Decide whether these are worth
   sending to a model at all.
5. Progress reporting: polling or streaming? Say why you picked yours and what it costs.

## Using AI tools

Use them. Claude, Copilot, Cursor, whatever you normally use. We use them too.

The condition: you own every line you submit. In the follow-up interview we will open
your repo, point at code, and ask why it is written that way, what a given type is at
that point, and what breaks if we delete a line. Candidates who cannot answer those
questions about their own submission do not advance, regardless of how good the code
looks. Do not submit code you have not read.

## Submitting

Push to a public GitHub repo and send us the link.

Your repo must have:

- `README.md` with setup steps that work on a clean machine. Assume the reviewer has
  Python and Node and nothing else. If a step is missing, we will not guess it.
- `DECISIONS.md` covering the five decisions above, what you noticed in the ticket
  data, what you would do with another day, and which parts you are least happy with.
  Half a page is plenty. Honest beats impressive here.
- `.env.example` listing every variable you read. No real keys, ever.
- Commit history that shows the work: a series of small commits with messages a
  reviewer can follow. One commit called "initial commit" containing the whole project
  is an automatic fail, even if the code is excellent.

We will clone it, follow your README, and expect to be looking at a working app inside
ten minutes. Test that path on a fresh clone before you send it.

Questions about the brief are welcome and never count against you. Email us.
