export const PRODUCTS = [
  'Zen Orchestrator',
  'Zen Studio',
  'Zen Connect',
  'Zen Insights',
  'Zen Vault',
] as const;
export const CATEGORIES = [
  'outage',
  'billing',
  'bug',
  'feature_request',
  'how_to',
  'churn_risk',
] as const;
export const SEVERITIES = ['low', 'medium', 'high', 'critical'] as const;
export const ACTIONS = ['refund', 'credit', 'fix', 'callback', 'information', 'none'] as const;
export const FIELDS = [
  'company',
  'product',
  'category',
  'severity',
  'requested_action',
  'refund_amount',
  'deadline',
  'escalated',
] as const;
export type FieldName = (typeof FIELDS)[number];

export interface Ticket {
  id: string;
  subject: string;
  body: string;
  channel: 'email' | 'chat' | 'web_form' | 'phone_transcript';
  received_at: string;
  from_email: string;
  attachments: number;
}

export type ItemStatus = 'queued' | 'running' | 'done' | 'needs_review' | 'failed';
export interface Job {
  id: string;
  state: 'queued' | 'running' | 'done' | 'cancelled';
  created_at: string;
  total: number;
  queued: number;
  running: number;
  done: number;
  failed: number;
  needs_review: number;
  items: { ticket_id: string; status: ItemStatus; record_id: string | null }[];
}

export interface FieldMeta {
  source: 'model' | 'human' | 'missing';
  grounding: 'grounded' | 'inferred' | 'missing';
  evidence: string | null;
}

export interface ReviewRecord {
  id: string;
  job_id: string;
  ticket_id: string;
  ticket: Ticket;
  values: Record<FieldName, string | number | boolean | null>;
  field_meta: Record<FieldName, FieldMeta>;
  status: 'done' | 'needs_review' | 'failed';
  schema_valid: boolean;
  reviewed: boolean;
  attempts: number;
  raw_outputs: string[];
  errors: { field: string; message: string }[];
  notes: string[];
  version: number;
}

export function humanEdited(record: ReviewRecord): boolean {
  return FIELDS.some((name) => record.field_meta[name].source === 'human');
}

export function label(value: string): string {
  return value.replaceAll('_', ' ');
}
