import { FIELDS, type ReviewRecord, type Ticket } from '../lib/types';

export const ticket: Ticket = {
  id: 'tkt_0005',
  subject: 'URGENT: platform unavailable',
  body: 'Acme: Zen Studio is unavailable. Please fix it urgently.',
  channel: 'email',
  received_at: '2026-08-15T16:04:20Z',
  from_email: 'support@acme.com',
  attachments: 0,
};

export function makeRecord(overrides: Partial<ReviewRecord> = {}): ReviewRecord {
  return {
    id: 'job:tkt_0005',
    job_id: 'job',
    ticket_id: ticket.id,
    ticket,
    values: {
      company: 'Acme',
      product: 'Zen Studio',
      category: 'outage',
      severity: 'critical',
      requested_action: 'fix',
      refund_amount: null,
      deadline: null,
      escalated: false,
    },
    field_meta: Object.fromEntries(
      FIELDS.map((name) => [
        name,
        {
          source: 'model',
          grounding: 'grounded',
          evidence: null,
        },
      ]),
    ) as ReviewRecord['field_meta'],
    status: 'needs_review',
    schema_valid: true,
    reviewed: false,
    attempts: 2,
    raw_outputs: [],
    errors: [],
    notes: [],
    version: 1,
    ...overrides,
  };
}
