import { useEffect, useState } from 'react';
import { ApiError, api } from '../lib/api';
import {
  ACTIONS,
  CATEGORIES,
  FIELDS,
  PRODUCTS,
  SEVERITIES,
  label,
  type FieldName,
  type ReviewRecord,
} from '../lib/types';
import { StatusBadge } from './StatusBadge';

const LABELS: Record<FieldName, string> = {
  company: 'Company',
  product: 'Product',
  category: 'Category',
  severity: 'Severity',
  requested_action: 'Requested action',
  refund_amount: 'Refund amount (USD)',
  deadline: 'Deadline',
  escalated: 'Escalated',
};
const OPTIONS: Partial<Record<FieldName, readonly string[]>> = {
  product: PRODUCTS,
  category: CATEGORIES,
  severity: SEVERITIES,
  requested_action: ACTIONS,
  escalated: ['true', 'false'],
};

function formValues(record: ReviewRecord): Record<FieldName, string> {
  return Object.fromEntries(
    FIELDS.map((name) => [name, record.values[name]?.toString() ?? '']),
  ) as Record<FieldName, string>;
}

function validationErrors(record: ReviewRecord): Record<string, string> {
  return Object.fromEntries(record.errors.map((error) => [error.field, error.message]));
}

export function RecordEditor({
  record,
  onSaved,
  onDirtyChange,
  onConflict,
}: {
  record: ReviewRecord;
  onSaved: (record: ReviewRecord) => void;
  onDirtyChange?: (dirty: boolean) => void;
  onConflict?: () => void;
}) {
  const [base, setBase] = useState(record);
  const [draft, setDraft] = useState(() => formValues(record));
  const [errors, setErrors] = useState(() => validationErrors(record));
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [activeField, setActiveField] = useState<FieldName | null>(null);
  const baseValues = formValues(base);
  const dirty = FIELDS.some((name) => draft[name] !== baseValues[name]);
  const conflict = record.version > base.version;

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  useEffect(() => {
    // Polling must never replace a reviewer's unsaved input.
    if (record.version > base.version && !dirty) {
      setBase(record);
      setDraft(formValues(record));
      setErrors(validationErrors(record));
    }
  }, [record, base.version, dirty]);

  useEffect(() => {
    if (!dirty) return;
    const warnBeforeLeaving = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warnBeforeLeaving);
    return () => window.removeEventListener('beforeunload', warnBeforeLeaving);
  }, [dirty]);

  function reloadRecord() {
    setBase(record);
    setDraft(formValues(record));
    setErrors(validationErrors(record));
    setMessage('');
  }

  function change(name: FieldName, value: string) {
    setDraft((previous) => ({ ...previous, [name]: value }));
    setErrors((previous) => {
      const next = { ...previous };
      delete next[name];
      return next;
    });
    setMessage('');
  }

  async function save(reviewed?: boolean) {
    const changes: Record<string, unknown> = {};
    for (const name of FIELDS) {
      if (draft[name] === baseValues[name]) continue;
      if (name === 'refund_amount') {
        if (draft[name] !== '' && !Number.isFinite(Number(draft[name]))) {
          setErrors((previous) => ({
            ...previous,
            refund_amount: 'Enter a finite number in USD.',
          }));
          return;
        }
        changes[name] = draft[name] === '' ? null : Number(draft[name]);
      } else if (name === 'escalated') {
        changes[name] = draft[name] === '' ? null : draft[name] === 'true';
      } else {
        changes[name] = name === 'deadline' && draft[name] === '' ? null : draft[name];
      }
    }
    setSaving(true);
    setMessage('');
    try {
      const updated = await api.patch(base, changes, reviewed);
      setBase(updated);
      setDraft(formValues(updated));
      setErrors(validationErrors(updated));
      setMessage(
        reviewed
          ? 'Reviewed and ready for export.'
          : 'Changes saved. Human-edited fields are marked.',
      );
      onSaved(updated);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields);
        setMessage(err.message);
        if (err.status === 409) onConflict?.();
      } else {
        setMessage(err instanceof Error ? err.message : 'Could not save changes.');
      }
    } finally {
      setSaving(false);
    }
  }

  const quote = activeField ? base.field_meta[activeField].evidence : null;
  const quoteIndex = quote ? record.ticket.body.indexOf(quote) : -1;

  return (
    <section className="review-detail panel" aria-label={`Review ${record.ticket_id}`}>
      <div className="detail-heading">
        <div>
          <span className="mono">{record.ticket_id}</span>
          <h2>{record.ticket.subject || '(No subject)'}</h2>
        </div>
        <StatusBadge status={base.reviewed ? 'reviewed' : base.status} />
      </div>
      {dirty && (
        <div className="draft-warning">
          You have unsaved edits. Save them before switching tickets.
        </div>
      )}
      {conflict && dirty && (
        <div className="error-banner" role="alert">
          A newer version is available. Your draft has been preserved.{' '}
          <button onClick={reloadRecord}>Discard draft and reload</button>
        </div>
      )}
      <div className="review-columns">
        <div className="source-pane">
          <div className="section-label">
            Original conversation <span>Read-only source</span>
          </div>
          <dl className="source-meta">
            <dt>From</dt>
            <dd>{record.ticket.from_email}</dd>
            <dt>Channel</dt>
            <dd>{label(record.ticket.channel)}</dd>
            <dt>Received</dt>
            <dd>{new Date(record.ticket.received_at).toLocaleString('en-GB')}</dd>
            <dt>Attachments</dt>
            <dd>
              {record.ticket.attachments}{' '}
              {record.ticket.attachments > 0 && '(contents unavailable)'}
            </dd>
          </dl>
          <pre className="source-body">
            {quote && quoteIndex >= 0 ? (
              <>
                {record.ticket.body.slice(0, quoteIndex)}
                <mark>{quote}</mark>
                {record.ticket.body.slice(quoteIndex + quote.length)}
              </>
            ) : (
              record.ticket.body
            )}
          </pre>
          <details className="raw-output">
            <summary>
              Raw provider output · {base.attempts} attempt{base.attempts === 1 ? '' : 's'}
            </summary>
            {base.raw_outputs.length ? (
              base.raw_outputs.map((raw, index) => (
                <div key={index}>
                  <strong>Attempt {index + 1}</strong>
                  <pre>{raw}</pre>
                </div>
              ))
            ) : (
              <p>No provider output. See review notes.</p>
            )}
          </details>
        </div>
        <div className="fields-pane">
          <div className="section-label">
            Extracted proposal{' '}
            <span>{base.schema_valid ? 'Schema valid' : 'Incomplete / invalid'}</span>
          </div>
          <p className="field-legend">
            <span className="legend-dot grounded" />
            Grounded <span className="legend-dot inferred" />
            Inferred / missing <span className="legend-dot human" />
            Human edited
          </p>
          <form
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              save();
            }}
          >
            <div className="fields-grid">
              {FIELDS.map((name) => {
                const meta = base.field_meta[name];
                const id = `${record.id}-${name}`;
                const options = OPTIONS[name];
                return (
                  <div className={`field ${name === 'company' ? 'field-wide' : ''}`} key={name}>
                    <div className="field-heading">
                      <label htmlFor={id}>{LABELS[name]}</label>
                      <span
                        className={`field-origin ${meta.source === 'human' ? 'human' : meta.grounding}`}
                      >
                        {meta.source === 'human' ? 'Human edited' : meta.grounding}
                      </span>
                    </div>
                    {options ? (
                      <select
                        id={id}
                        value={draft[name]}
                        onChange={(event) => change(name, event.target.value)}
                        onFocus={() => setActiveField(name)}
                        aria-invalid={Boolean(errors[name])}
                        aria-describedby={errors[name] ? `${id}-error` : undefined}
                      >
                        <option value="">Choose a value…</option>
                        {options.map((value) => (
                          <option key={value} value={value}>
                            {name === 'escalated'
                              ? value === 'true'
                                ? 'Yes'
                                : 'No'
                              : label(value)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        id={id}
                        type={
                          name === 'refund_amount'
                            ? 'number'
                            : name === 'deadline'
                              ? 'date'
                              : 'text'
                        }
                        min={name === 'refund_amount' ? '0' : undefined}
                        step={name === 'refund_amount' ? '0.01' : undefined}
                        value={draft[name]}
                        placeholder={name === 'company' ? 'Enter company name' : 'Optional'}
                        onChange={(event) => change(name, event.target.value)}
                        onFocus={() => setActiveField(name)}
                        aria-invalid={Boolean(errors[name])}
                        aria-describedby={errors[name] ? `${id}-error` : undefined}
                      />
                    )}
                    {errors[name] && (
                      <p className="field-error" id={`${id}-error`} role="alert">
                        {errors[name]}
                      </p>
                    )}
                    {meta.evidence && (
                      <p className="field-evidence" title={meta.evidence}>
                        “{meta.evidence}”
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
            {errors.record && (
              <p className="field-error" role="alert">
                {errors.record}
              </p>
            )}
            {base.notes.length > 0 && (
              <div className="review-notes">
                <strong>Review notes</strong>
                <ul>
                  {base.notes.map((note, index) => (
                    <li key={index}>{note}</li>
                  ))}
                </ul>
                <p>Notes describe the original extraction and remain visible after correction.</p>
              </div>
            )}
            <div className="save-bar">
              <button className="button" type="submit" disabled={!dirty || saving || conflict}>
                Save changes
              </button>
              <button
                className="button primary"
                type="button"
                disabled={saving || conflict || (base.reviewed && !dirty)}
                onClick={() => save(true)}
              >
                {saving ? 'Saving…' : 'Approve & save'} <span aria-hidden="true">✓</span>
              </button>
            </div>
            {message && (
              <p className="save-message" role="status">
                {message}
              </p>
            )}
            <p className="review-help">
              Approval confirms the whole record and makes it eligible for CSV export.
            </p>
          </form>
        </div>
      </div>
    </section>
  );
}
