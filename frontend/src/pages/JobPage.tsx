import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../lib/api';
import { type Job, type ReviewRecord } from '../lib/types';

export function JobPage() {
  const { id = '' } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [records, setRecords] = useState<ReviewRecord[]>([]);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);

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
        setRecords(result.records);
        setError('');
        if (progress.state === 'running' || progress.state === 'queued') timer = setTimeout(poll, 1000);
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'Could not load job.');
      }
    }
    poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [id, reload]);

  return (
    <>
      <Link className="back-link" to="/">← Ticket inbox</Link>
      <div className="page-heading"><div><p className="eyebrow">02 / EXTRACT & REVIEW</p><h1>Review workbench</h1><p className="subtitle mono">Job {id.slice(0, 12)}</p></div>{job && <StatusBadge status={job.state} />}</div>
      {error && <div className="error-banner" role="alert">{error} <button onClick={() => setReload(reload + 1)}>Retry</button></div>}
      {!job ? <div className="empty-state">{error ? 'Job unavailable.' : 'Loading extraction job…'}</div> : (
        <>
          <section className="panel progress-panel"><div className="progress-label"><strong>{job.state === 'done' ? 'Processing complete' : job.state === 'cancelled' ? 'Processing cancelled' : 'Extracting tickets…'}</strong><span>{job.done + job.failed} / {job.total} processed</span></div><progress max={job.total} value={job.done + job.failed} aria-label="Extraction progress" /><div className="progress-counts"><span>{job.queued} queued</span><span>{job.running} running</span><span>{job.done} processed</span><span>{job.failed} failed</span><span>{job.needs_review} need review</span></div></section>
          <section className="panel"><div className="toolbar"><h2>Batch items</h2><span className="muted">{records.length} results available</span></div><div className="item-grid">{job.items.map(item => <div className="item-card" key={item.ticket_id}><span className="mono">{item.ticket_id}</span><StatusBadge status={item.status} /></div>)}</div></section>
        </>
      )}
    </>
  );
}
