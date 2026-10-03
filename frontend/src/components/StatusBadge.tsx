import { label } from '../lib/types';

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{label(status)}</span>;
}
