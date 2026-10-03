import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { type Job } from '../lib/types';
import { JobPage } from '../views/JobPage';
import { makeRecord } from './fixtures';

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>();
  return { ...actual, api: { ...actual.api, job: vi.fn(), results: vi.fn() } };
});

it('shows an individual result before the batch completes and stops polling at done', async () => {
  const running: Job = {
    id: 'job',
    state: 'running',
    created_at: '2026-08-15T00:00:00Z',
    total: 2,
    queued: 0,
    running: 1,
    done: 1,
    failed: 0,
    needs_review: 1,
    items: [
      { ticket_id: 'tkt_0005', status: 'needs_review', record_id: 'job:tkt_0005' },
      { ticket_id: 'tkt_0006', status: 'running', record_id: null },
    ],
  };
  vi.mocked(api.job)
    .mockResolvedValueOnce(running)
    .mockResolvedValue({ ...running, state: 'done', running: 0, done: 2 });
  vi.mocked(api.results).mockResolvedValue({ records: [makeRecord()] });
  render(<JobPage id="job" />);
  expect(await screen.findByLabelText('Review tkt_0005')).toBeInTheDocument();
  expect(screen.getByText('Extracting tickets…')).toBeInTheDocument();
  expect(screen.queryByText('Processing complete')).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getByText('Processing complete')).toBeInTheDocument(), {
    timeout: 2000,
  });
  expect(api.job).toHaveBeenCalledTimes(2);
  expect(api.results).toHaveBeenCalledTimes(2);
});

it('keeps an edited record selected when a ticket earlier in the sort order finishes', async () => {
  vi.clearAllMocks();
  const first = makeRecord();
  const later = makeRecord({
    id: 'job:tkt_0003',
    ticket_id: 'tkt_0003',
    ticket: { ...first.ticket, id: 'tkt_0003', subject: 'Earlier ticket' },
  });
  const progress: Job = {
    id: 'job',
    state: 'running',
    created_at: '2026-08-15T00:00:00Z',
    total: 2,
    queued: 0,
    running: 1,
    done: 1,
    failed: 0,
    needs_review: 1,
    items: [
      { ticket_id: 'tkt_0005', status: 'needs_review', record_id: first.id },
      { ticket_id: 'tkt_0003', status: 'running', record_id: null },
    ],
  };
  vi.mocked(api.job)
    .mockResolvedValueOnce(progress)
    .mockResolvedValue({ ...progress, state: 'done', running: 0, done: 2 });
  vi.mocked(api.results)
    .mockResolvedValueOnce({ records: [first] })
    .mockResolvedValue({ records: [later, first] });
  render(<JobPage id="job" />);
  await screen.findByLabelText('Company');
  const user = userEvent.setup();
  await user.clear(screen.getByLabelText('Company'));
  await user.type(screen.getByLabelText('Company'), 'Unsaved company');
  await waitFor(() => expect(screen.getByText('Processing complete')).toBeInTheDocument(), {
    timeout: 2000,
  });
  expect(screen.getByLabelText('Company')).toHaveValue('Unsaved company');
  expect(screen.getByLabelText('Review tkt_0005')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /tkt_0003.*Earlier ticket/ }));
  expect(screen.getByText(/Save your edits before switching/)).toBeInTheDocument();
  expect(screen.getByLabelText('Company')).toHaveValue('Unsaved company');
  await user.click(screen.getByRole('button', { name: 'Discard and switch' }));
  expect(screen.getByLabelText('Review tkt_0003')).toBeInTheDocument();
  expect(screen.getByLabelText('Company')).toHaveValue('Acme');
});
