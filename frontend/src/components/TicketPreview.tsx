import { useEffect, useRef } from 'react';
import { label, type Ticket } from '../lib/types';

export function TicketPreview({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    // A native modal handles focus trapping, Escape, and focus restoration.
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className="ticket-dialog"
      aria-labelledby="ticket-preview-heading"
      onClose={onClose}
    >
      <div className="ticket-dialog-heading">
        <div>
          <p className="eyebrow">{ticket.id} / ORIGINAL TICKET</p>
          <h2 id="ticket-preview-heading">{ticket.subject || '(No subject)'}</h2>
        </div>
        <button className="button" onClick={() => dialogRef.current?.close()} autoFocus>
          Close
        </button>
      </div>
      <div className="ticket-dialog-content">
        <dl className="source-meta">
          <dt>From</dt>
          <dd>{ticket.from_email}</dd>
          <dt>Channel</dt>
          <dd>{label(ticket.channel)}</dd>
          <dt>Received</dt>
          <dd>
            <time dateTime={ticket.received_at}>
              {new Date(ticket.received_at).toLocaleString('en-GB')}
            </time>
          </dd>
          <dt>Attachments</dt>
          <dd>{ticket.attachments} (count only; files are not supplied)</dd>
        </dl>
        <p className="section-label">Full conversation · Read-only source</p>
        <pre className="source-body">{ticket.body}</pre>
      </div>
    </dialog>
  );
}
