# Verification record — 3 October 2026

Verified commit `7b2ba81` from a fresh local Git clone, without copying `.env`,
installed packages, or generated files from the working directory.

Environment: Windows, Python 3.14.7, Node.js 24.20.0, npm 11.19.0.

- Created a new virtual environment and installed `backend/requirements.txt`.
- Installed frontend dependencies with `npm ci`: zero reported vulnerabilities.
- Backend: 29 tests passed; Ruff lint and format checks passed.
- Frontend: 7 tests passed; Prettier check and TypeScript/production build passed.
- Started FastAPI and the built frontend preview on separate verification ports.
- Verified health through the frontend proxy, all 150 tickets, and SPA route fallback.
- Opened that clean-clone preview in the browser, selected eight tickets,
  and confirmed all eight reached terminal results without provider failures.
- Earlier browser checks on the working checkout verified incremental results,
  invalid approval feedback, correction, human provenance, approval, and CSV download.
  The exported row preserved the edited product/severity and matching provenance.
- Checked desktop source/field layout and a narrow viewport without horizontal overflow.
- Confirmed the original dataset has no changes from its preservation commit.

These checks validate the mock workflow. Gemini transport is simulated in tests;
live Gemini calls and semantic extraction accuracy were not verified. Installation
used locally cached downloads; download time on another machine depends on its network.
State remains process-local, and the frontend's Vite choice departs from the brief.

## Gemini integration verification — 4 October 2026

- Configured a local ignored `backend/.env` with Gemini mode and a private API key.
- A live `gemini-3.1-flash-lite` request returned a valid structured extraction.
- Ran `backend/scripts/smoke_gemini.py` against an isolated FastAPI application with
  two invented tickets and a sparse `?` ticket. All three reached terminal results
  with zero failures; the sparse ticket correctly skipped the provider call.
- Verified outage/billing categories, exact USD refund extraction, field validation,
  a human correction, approval, stale-version rejection, and one-row reviewed CSV.
- The script created temporary synthetic data and did not send assignment tickets
  or change jobs in the running application.
- Fixed automated test isolation: local dotenv files and provider environment
  overrides no longer affect test settings or cause real Gemini calls.
- Backend: all 30 tests and Ruff lint passed while local Gemini mode was configured.
- Frontend: all eight tests, production build, and Prettier check passed.
- Restarted FastAPI in Gemini mode. Health through the Vite proxy returned
  `{"status":"ok","provider":"gemini"}`; the inbox loaded all 150 source tickets.
- The browser displayed **Gemini provider** and the full inbox.

This validates the live integration on invented examples. Accuracy and throughput
on a real 150-ticket Gemini batch have not been evaluated. Account quota still applies.

## Required-field review routing — 4 October 2026

Historical check: the optional-value fallback described below was superseded by
the strict retry correction recorded later in this document.

- Changed extraction and human-edit routing to use required-field completeness.
  Missing quotes, inferred values, notes, and absent optional fields no longer force
  complete records into review. Invalid required values remain missing in the draft.
- After one unsuccessful provider repair, an individually validated draft can finish
  with invalid optional values left empty; complete Pydantic validation is still
  required. Raw attempts and explanatory notes are preserved.
- Backend: 48 tests passed; Ruff lint passed. Added checks for every required field
  being absent/null, optional omission, informational notes, unmatched evidence,
  invalid optional values, completion after edits, and separate export approval.
- Offline mock processing of all 150 assignment tickets completed with zero failures:
  22 Done and 128 Needs review. Every review draft lacked at least one valid required
  field; 126 lacked severity under the conservative mock rules. These are mock counts,
  not Gemini results or accuracy measurements.
- Repeated the live synthetic Gemini smoke test: both complete invented records were
  Done; only the sparse `?` record needed review. Corrections, approval, versions, and
  reviewed CSV passed. No assignment tickets were sent for this verification.
- Restarted the running Gemini backend to load the updated routing policy.

## Next.js App Router migration - 4 October 2026

- Migration commit `8c34ce2` replaces the Vite application server and React Router
  with Next.js 16.3.8 App Router. Vite remains only in the Vitest test tooling.
- Verified development and production startup, `/`, direct `/jobs/[id]` visits,
  unknown-page HTTP 404 responses, and API forwarding to the existing Gemini backend.
  The frontend remains on port 5173. No assignment tickets were sent to Gemini.
- Backend: 48 tests passed; Ruff lint and formatting checks passed.
- Frontend: eight tests passed; TypeScript, Prettier, and Next.js production build passed.
- Cloned `8c34ce2` into a fresh directory, created a new Python virtual environment,
  installed requirements, and ran `npm ci` without copying dotenv files or installed
  dependencies. Package downloads used local caches; npm reported zero vulnerabilities.
- The fresh clone passed its production build, eight frontend tests, and formatting.
  On separate verification ports, its default no-key mock backend and Next.js server
  passed an HTTP workflow through the frontend's API rewrite: HTTP 202, progress
  arithmetic, repair retry, a twice-invalid required-field draft, human correction,
  field provenance, reviewed CSV, and a direct dynamic job-page visit.
- A browser check confirmed the fresh-clone workbench displayed both completed
  results, the needs-review item first, field errors, human provenance, and export.
- Updated setup/configuration/interview notes and regenerated the ten-page specification
  PDF. Rendered every page and checked layout, including complete enum values in the
  schema table. The PDF build script is optional and requires ReportLab.

Frontend framework compliance was resolved by this migration. The retry-routing
departure present at that point was corrected in the later strict retry update.

## Strict retry and final workflow verification - 4 October 2026

- Commit `88b2c6d` makes every second validation failure stay in needs_review,
  including invalid optional values, unknown fields, malformed JSON, and invalid
  envelopes. Both raw outputs, final errors, and usable draft fields are preserved.
- Added regression tests for repaired optional values, repeated optional/extra-field
  failure, an invalid second envelope after a usable first draft, job completion,
  and explicit approval/export of a rejected draft with an empty optional value.
- Commit `2f91ddb` removes the eight-ticket selection shortcut and its UI copy.
  The assignment-required deterministic mock and its deliberate invalid outputs remain.
- Backend: all 55 tests, Ruff lint, and formatting checks passed. The suite includes
  offline processing of all 150 source tickets with correct terminal progress and
  zero provider failures.
- Frontend: all eight tests, Prettier, TypeScript, and Next.js production build passed.
- Cloned `2f91ddb` into a new directory without copied dotenv files or dependencies.
  Created a virtual environment, installed requirements, and ran npm ci. The clone
  passed the same 55 backend/eight frontend tests, lint/format checks, and production build.
  Downloads used local caches; npm reported zero vulnerabilities.
- Started the clone's default mock backend and production Next.js server on separate
  verification ports. Confirmed 150 source tickets, HTTP 202, early results while the
  job was running, progress arithmetic, one repaired output, one twice-rejected output,
  sparse-input skipping, field-specific HTTP 422, human provenance, stale HTTP 409,
  one-row reviewed CSV with correct headers, direct job rendering, and unknown-page 404.
- No assignment tickets were sent to Gemini. Test edits were confined to the isolated
  verification app; the original dataset was not modified.
- Updated README, DECISIONS, interview notes, and the companion PDF to describe the
  strict retry rule and the single ticket-selection workflow.
- Browser inspection confirmed the mock job's review ordering, human-edit indicator,
  approved-only export, and the main inbox's 150-ticket selection without a demo shortcut.
  Restarted the local Gemini backend to load the fix; no extraction calls were made.
- Regenerated the ten-page specification PDF, rendered every page, and checked the
  layout and schema table. PDF text checks confirmed the updated validation policy.

## Inbox ticket preview - 4 October 2026

- Added a View ticket action for each inbox row. The native modal shows the full
  original body, subject, sender, channel, received time, and attachment count.
- Viewing does not create a job or change selection. The preview is read-only;
  Close and Escape return to the inbox. Long bodies scroll with the close header visible.
- All nine frontend tests passed, including preservation of the complete body and
  newlines, metadata, selection, and absence of an extraction call when previewing.
  TypeScript, Prettier, and the Next.js production build passed.
- Browser checks covered the forwarded tkt_0089 chain, sparse tkt_0020 with an empty
  subject, initial focus, Escape dismissal, focus restoration, and retained selection.
  No tickets were submitted to Gemini during these checks.
