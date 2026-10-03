# Dataset notes: tickets.jsonl

150 lines, one JSON object per line, UTF-8. Received dates span 4 to 30 August 2026.

## Fields

| field | type | notes |
| --- | --- | --- |
| `id` | string | `tkt_0001` style |
| `subject` | string | sometimes empty |
| `body` | string | raw text, newlines preserved |
| `channel` | string | `email`, `web_form`, `chat`, `phone_transcript` |
| `received_at` | string | ISO 8601 with `Z` |
| `from_email` | string | |
| `attachments` | number | count only, no files provided |

## What is in the bodies

Roughly two thirds are single-message emails. The rest include quoted reply chains,
email signatures, confidentiality footers, and one call transcript with speaker labels.
Amounts appear as `$18,400`, `4 820 EUR`, and "about nine thousand something". Dates
appear as "the 14th", "Thursday", "before quarter end", and real dates.

Specific tickets worth opening before you design your prompt:

- `tkt_0004` body is `please advise`. `tkt_0020` body is `?` with an empty subject.
- `tkt_0058` is in French and quotes an amount in EUR.
- `tkt_0089` is a forwarded escalation chain with three distinct problems, two
  plausible categories, and a non-renewal threat.
- `tkt_0105` is written in heavy shorthand with several typos.
- `tkt_0131` is a phone transcript where the amount is spoken, not written.

None of these are edge cases we invented to catch you out. They are the shapes real
support inboxes contain, and the reason a human sits in this loop at all.
