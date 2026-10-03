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
