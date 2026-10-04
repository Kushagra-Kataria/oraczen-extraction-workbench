'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { StatusBadge } from '../components/StatusBadge';
import { RecordEditor } from '../components/RecordEditor';
import { api } from '../lib/api';
import { humanEdited, type Job, type ReviewRecord } from '../lib/types';

export function JobPage({ id }: { id: string }) {
  const [job, setJob] = useState<Job | null>(null);
  const [records, setRecords] = useState<ReviewRecord[]>([]);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [activeId, setActiveId] = useState('');
  const [filter, setFilter] = useState('all');
  const [cancelling, setCancelling] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editorEpoch, setEditorEpoch] = useState(0);
  const [pendingSwitch, setPendingSwitch] = useState<{ id: string; filter: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const progress = await api.job(id, controller.signal);
        // Fetch results after progress so a terminal snapshot includes the last result.
        const result = await api.results(id, controller.signal);
        if (controller.signal.aborted) return;
        setJob(progress);
        // Ignore an older polling response that arrived after a successful human save.
        setRecords((previous) =>
          result.records.map((remote) => {
            const local = previous.find((item) => item.id === remote.id);
            return local && local.version > remote.version ? local : remote;
          }),
        );
        setError('');
        if (progress.state === 'running' || progress.state === 'queued')
          timer = setTimeout(poll, 1000);
      } catch (err) {
        if (!controller.signal.aborted)
          setError(err instanceof Error ? err.message : 'Could not load job.');
      }
    }
    poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [id, reload]);

  const visible = records
    .filter(
      (record) =>
        filter === 'all' ||
        (filter === 'human'
          ? humanEdited(record)
          : filter === 'reviewed'
            ? record.reviewed
            : record.status === filter),
    )
    .sort((a, b) => {
      const rank = { needs_review: 0, failed: 1, done: 2 };
      return rank[a.status] - rank[b.status] || a.ticket_id.localeCompare(b.ticket_id);
    });
  const active = visible.find((record) => record.id === activeId) || visible[0];
  const approved = records.filter((record) => record.reviewed).length;

  useEffect(() => {
    // Keep the first selected result stable when earlier ticket IDs finish later.
    if (!editing && visible.length && !visible.some((record) => record.id === activeId)) {
      setActiveId(visible[0].id);
    }
  }, [visible, activeId, editing]);

  function switchReview(nextId: string, nextFilter: string) {
    if (editing) {
      setPendingSwitch({ id: nextId, filter: nextFilter });
      return;
    }
    setActiveId(nextId);
    setFilter(nextFilter);
  }

  function discardAndSwitch() {
    if (!pendingSwitch) return;
    setEditing(false);
    setEditorEpoch((value) => value + 1);
    setActiveId(pendingSwitch.id);
    setFilter(pendingSwitch.filter);
    setPendingSwitch(null);
  }

  function saved(updated: ReviewRecord) {
    setPendingSwitch(null);
    setRecords((previous) =>
      previous.map((record) => (record.id === updated.id ? updated : record)),
    );
    setJob((previous) => {
      if (!previous) return previous;
      const items = previous.items.map((item) =>
        item.record_id === updated.id ? { ...item, status: updated.status } : item,
      );
      return {
        ...previous,
        items,
        done: items.filter((item) => item.status === 'done' || item.status === 'needs_review')
          .length,
        failed: items.filter((item) => item.status === 'failed').length,
        needs_review: items.filter((item) => item.status === 'needs_review').length,
      };
    });
  }

  async function cancel() {
    setCancelling(true);
    try {
      setJob(await api.cancel(id));
      setReload((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not cancel job.');
    } finally {
      setCancelling(false);
    }
  }

  return (
    <>
      <Link className="back-link" href="/">
        <span aria-hidden="true">←</span>
        Back to ticket inbox
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">02 / EXTRACT & REVIEW</p>
          <h1>Review workbench</h1>
          <p className="subtitle mono">Job {id.slice(0, 12)}</p>
        </div>
        <div className="heading-actions">
          {job && <StatusBadge status={job.state} />}
          <button className="button" onClick={() => setReload((value) => value + 1)}>
            Refresh
          </button>
          <a
            className={`button primary ${!approved ? 'disabled-link' : ''}`}
            aria-disabled={!approved}
            href={approved ? api.exportUrl(id) : undefined}
          >
            Export reviewed ({approved}) ↓
          </a>
        </div>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error} <button onClick={() => setReload(reload + 1)}>Retry</button>
        </div>
      )}
      {!job ? (
        <div className="empty-state">{error ? 'Job unavailable.' : 'Loading extraction job…'}</div>
      ) : (
        <>
          <section className="panel progress-panel">
            <div className="progress-label">
              <strong>
                {job.state === 'done'
                  ? 'Processing complete'
                  : job.state === 'cancelled'
                    ? 'Processing cancelled'
                    : 'Extracting tickets…'}
              </strong>
              <span>
                {job.done + job.failed} / {job.total} processed
              </span>
            </div>
            <progress
              max={job.total}
              value={job.done + job.failed}
              aria-label="Extraction progress"
            />
            <div className="progress-counts">
              <span>{job.queued} queued</span>
              <span>{job.running} running</span>
              <span>{job.done} processed</span>
              <span>{job.failed} failed</span>
              <span>{job.needs_review} need review</span>
              {(job.state === 'running' || job.state === 'queued') && (
                <button
                  className="text-button cancel-button"
                  disabled={cancelling}
                  onClick={cancel}
                >
                  {cancelling ? 'Cancelling…' : 'Cancel job'}
                </button>
              )}
            </div>
          </section>
          <details className="panel batch-details">
            <summary>
              Batch items · {records.length} / {job.total} results available
            </summary>
            <div className="item-grid">
              {job.items.map((item) => (
                <button
                  className="item-card"
                  disabled={!item.record_id}
                  key={item.ticket_id}
                  onClick={() => switchReview(item.record_id!, 'all')}
                >
                  <span className="mono">{item.ticket_id}</span>
                  <StatusBadge status={item.status} />
                </button>
              ))}
            </div>
          </details>
          <div className="review-toolbar">
            <h2>
              Review queue <span className="muted">({visible.length})</span>
            </h2>
            <select
              aria-label="Filter review queue"
              value={filter}
              onChange={(event) => switchReview('', event.target.value)}
            >
              <option value="all">All results</option>
              <option value="needs_review">Needs review</option>
              <option value="human">Human edited</option>
              <option value="reviewed">Reviewed</option>
              <option value="failed">Failed</option>
            </select>
            <span className="muted">Only approved records are exported.</span>
          </div>
          {pendingSwitch && (
            <div className="info-strip" role="alert">
              <span>Save your edits before switching, or discard this draft.</span>
              <button className="text-button" onClick={() => setPendingSwitch(null)}>
                Keep editing
              </button>
              <button className="text-button" onClick={discardAndSwitch}>
                Discard and switch
              </button>
            </div>
          )}
          <div className="review-workspace">
            <aside className="review-queue" aria-label="Review queue">
              {visible.map((record) => (
                <button
                  key={record.id}
                  className={`queue-card ${active?.id === record.id ? 'active' : ''}`}
                  onClick={() => {
                    if (record.id !== active?.id) switchReview(record.id, filter);
                  }}
                >
                  <div>
                    <span className="mono">{record.ticket_id}</span>
                    <StatusBadge status={record.reviewed ? 'reviewed' : record.status} />
                  </div>
                  <strong>{record.ticket.subject || '(No subject)'}</strong>
                  <p>{record.values.company?.toString() || 'Company unresolved'}</p>
                  {humanEdited(record) && <small>Human edited</small>}
                </button>
              ))}
            </aside>
            {active ? (
              <RecordEditor
                key={`${active.id}:${editorEpoch}`}
                record={active}
                onSaved={saved}
                onDirtyChange={setEditing}
                onConflict={() => setReload((value) => value + 1)}
              />
            ) : (
              <div className="panel empty-state">
                {job.state === 'running' || job.state === 'queued'
                  ? 'Results will appear here as tickets finish.'
                  : 'No records match this filter.'}
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}
