import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { label, type Ticket } from '../lib/types';

const DEMO_IDS = [
  'tkt_0003',
  'tkt_0004',
  'tkt_0005',
  'tkt_0020',
  'tkt_0058',
  'tkt_0089',
  'tkt_0105',
  'tkt_0131',
];

export function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [channel, setChannel] = useState('all');
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    api
      .tickets(controller.signal)
      .then((data) => setTickets(data.tickets))
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [reload]);

  const visible = useMemo(
    () =>
      tickets.filter((ticket) => {
        const matchesChannel = channel === 'all' || ticket.channel === channel;
        const searchable =
          `${ticket.id} ${ticket.subject} ${ticket.body} ${ticket.from_email}`.toLowerCase();
        return matchesChannel && searchable.includes(query.toLowerCase());
      }),
    [tickets, channel, query],
  );

  function toggle(id: string) {
    setSelected((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleVisible() {
    const allSelected = visible.every((ticket) => selected.has(ticket.id));
    setSelected((previous) => {
      const next = new Set(previous);
      for (const ticket of visible) {
        if (allSelected) next.delete(ticket.id);
        else next.add(ticket.id);
      }
      return next;
    });
  }

  function selectAllTickets() {
    setSelected(new Set(tickets.map((ticket) => ticket.id)));
  }

  async function start() {
    setStarting(true);
    setError('');
    try {
      const job = await api.start([...selected]);
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start extraction.');
      setStarting(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">01 / SELECT</p>
          <h1>From conversations to clarity.</h1>
          <p className="subtitle">
            Choose support tickets. Extract a proposal. Review every uncertain detail.
          </p>
        </div>
        <button className="button primary" disabled={!selected.size || starting} onClick={start}>
          {starting
            ? 'Starting…'
            : `Extract ${selected.size || ''} ticket${selected.size === 1 ? '' : 's'}`}{' '}
          <span aria-hidden="true">→</span>
        </button>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <span>Support tickets</span>
          <strong>{loading ? '—' : tickets.length}</strong>
          <small>Original source preserved</small>
        </div>
        <div className="stat">
          <span>Input channels</span>
          <strong>4</strong>
          <small>Email, chat, form, phone</small>
        </div>
        <div className="stat">
          <span>Selected for extraction</span>
          <strong>{selected.size.toString().padStart(2, '0')}</strong>
          <small>Bounded background processing</small>
        </div>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          {error} <button onClick={() => setReload(reload + 1)}>Retry loading</button>
        </div>
      )}
      <div className="info-strip">
        <span className="info-icon" aria-hidden="true">
          i
        </span>
        <span>
          Run any selected batch, or load the review demo to see retry repair, missing information,
          French currency, and multiple issues.
        </span>
        <button
          className="text-button"
          disabled={loading || !tickets.length}
          onClick={selectAllTickets}
        >
          Select all {tickets.length} tickets →
        </button>
        <button
          className="text-button"
          disabled={loading}
          onClick={() =>
            setSelected(
              new Set(DEMO_IDS.filter((id) => tickets.some((ticket) => ticket.id === id))),
            )
          }
        >
          Load review demo (8) →
        </button>
      </div>

      <section className="panel" aria-label="Ticket inbox">
        <div className="toolbar">
          <label className="search-field">
            <span aria-hidden="true">⌕</span>
            <input
              aria-label="Search tickets"
              placeholder="Search tickets, companies, or products…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <select
            aria-label="Filter by channel"
            value={channel}
            onChange={(event) => setChannel(event.target.value)}
          >
            <option value="all">All channels</option>
            {['email', 'chat', 'web_form', 'phone_transcript'].map((value) => (
              <option key={value} value={value}>
                {label(value)}
              </option>
            ))}
          </select>
          <span className="muted toolbar-count">{visible.length} tickets</span>
          {selected.size > 0 && (
            <button className="text-button" onClick={() => setSelected(new Set())}>
              Clear selection
            </button>
          )}
        </div>
        {loading ? (
          <div className="empty-state" role="status">
            Loading the ticket inbox…
          </div>
        ) : (
          <div className="table-scroll">
            <table className="ticket-table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      aria-label="Select all filtered tickets"
                      checked={
                        visible.length > 0 && visible.every((ticket) => selected.has(ticket.id))
                      }
                      disabled={!visible.length}
                      onChange={toggleVisible}
                    />
                  </th>
                  <th>Ticket & conversation</th>
                  <th>Channel</th>
                  <th>Received</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((ticket) => (
                  <tr key={ticket.id} className={selected.has(ticket.id) ? 'selected-row' : ''}>
                    <td>
                      <input
                        type="checkbox"
                        aria-label={`Select ${ticket.id}`}
                        checked={selected.has(ticket.id)}
                        onChange={() => toggle(ticket.id)}
                      />
                    </td>
                    <td>
                      <div className="ticket-title">
                        <span className="mono">{ticket.id}</span>
                        <strong>{ticket.subject || '(No subject)'}</strong>
                        {ticket.body.length < 15 && (
                          <span className="badge badge-needs_review">Sparse</span>
                        )}
                      </div>
                      <p className="ticket-preview">{ticket.body.slice(0, 190)}</p>
                    </td>
                    <td>
                      <span className="channel">{label(ticket.channel)}</span>
                    </td>
                    <td className="date-cell">
                      {new Date(ticket.received_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visible.length === 0 && (
              <div className="empty-state">No tickets match these filters.</div>
            )}
          </div>
        )}
        <div className="panel-footer">
          {selected.size} selected across all filters <span>150 source tickets · August 2026</span>
        </div>
      </section>
    </>
  );
}
