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
- Opened that clean-clone preview in the browser, selected the eight-ticket demo,
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
