# Mock text processing

The mock provider separates customer issue text from recognizable email boilerplate
before applying extraction rules. This prevents a confidentiality footer such as
"received this in error" from turning a quota question into a bug report.
The approach uses message structure and phrase patterns, not ticket IDs or stored
expected answers.

## Text views and original source

`backend/app/providers/ticket_text.py` builds four views: current issue content,
quoted issue content, current identity text, and quoted identity text. The identity
views retain signatures for company extraction; the issue views exclude them.
The original Ticket is never modified. The UI still receives the complete subject,
body, signatures, footers, and reply chain, and the shared extraction pipeline
checks evidence against that original source.

Recognizable confidentiality notices and wrapped footer paragraphs are excluded.
Mobile-client notices, print/environment notices, reply separators, and transport
headers are handled separately. A footer paragraph ends at a blank line or message
boundary. A signature begins at a common sign-off, `--`, or a recognizable identity
line. Quote-depth changes and reply headers reset these states, so one message's
signature or footer cannot suppress the next quoted message.

Quote markers are removed only in the derived views. Customer phrases remain
unchanged: an evidence quote such as "drops rows" still exists in the original
quoted line. Quoted issues are retained rather than discarded, and a visible note
asks the reviewer to verify their current status.

## Rule selection

- Specific issue patterns are checked in current content, quoted context, then the
  subject. Within a source, category priority remains churn risk, billing, outage,
  feature request, then bug. General how-to questions are considered after these
  issue patterns, so a follow-up question does not hide a quoted unresolved problem.
- A bare `error` is no longer a bug rule. Bug evidence includes concrete phrases
  such as `returns an error`, an error code, errors during an operation, dropped
  rows, apostrophe failures, and incorrect export formatting. An error-notification
  settings question can therefore remain how_to.
- Company extraction prefers current identity text and falls back to quoted
  identity text. Signatures are available for this purpose without their job titles
  or company names becoming severity, category, or escalation signals.
- Product, severity, actions, amounts, deadlines, and escalation rules use the
  cleaned issue views. Current requested actions take precedence over quoted ones;
  support-agent suggestions in phone transcripts remain excluded from action rules.
- Refund parsing prefers amounts in the selected action's text, falling back to
  meaningful conversation context when no currency/amount is present there. EUR
  remains unresolved in the USD field. Signature/footer prices and dates do not
  become business values.
- Multi-issue notes are derived from matched issue types rather than a special
  case for tkt_0089. Existing intentional grading failures remain limited to
  tkt_0005's first severity and tkt_0003's product on both attempts.

The provider remains deterministic. Its configurable artificial delay, async
`extract(ticket, feedback)` interface, raw JSON proposals, one repair attempt,
Pydantic validation, and human approval/export flow are unchanged.

## Verification

Ten new invented-ticket regressions cover four confidentiality-footer variants,
a genuine product error, quoted unresolved issues, quoted escalation, signature
company extraction, footer leakage into other fields, and an error-settings question.
All 65 backend tests, Ruff lint, and Ruff formatting checks passed.

Local mock inspection of tkt_0001 produced:

| Field | Result |
| --- | --- |
| company | Castlerock Mining; grounded in the preserved signature |
| product | Zen Orchestrator |
| category | how_to; evidence: `does Zen Orchestrator count` |
| severity | null; impact is not supplied |
| requested_action | information |
| refund_amount / deadline | null / null |
| escalated | false |
| status / attempts | needs_review / 2, because required severity remains missing |

The 150-ticket offline mock run completed with 22 Done, 128 Needs review, and zero
provider failures. These counts describe validation routing, not accuracy. The
source file's hash was unchanged. No tickets were sent to Gemini for this fix.

## Limitations

These are conservative heuristics, not an email parser or a semantic model. Custom
footers, unfamiliar languages, unusual signatures, and malformed reply layouts may
not be recognized. A sign-off embedded in the middle of a message can be ambiguous.
Quoted text can describe an old resolved issue; retaining it preserves useful
context but does not establish that it remains actionable. The current request
has priority when it contains a specific issue or action, and original text and
notes remain available for review.

Phrase rules do not resolve negation, every paraphrase, company identity conflicts,
or every historical amount/date. Exact source quotes establish presence, not
semantic correctness. Missing facts remain unresolved, and Done does not grant
approval for CSV export.
