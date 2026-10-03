import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { type Job } from '../lib/types';
import { JobPage } from '../pages/JobPage';
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
  render(
    <MemoryRouter initialEntries={['/jobs/job']}>
      <Routes>
        <Route path="/jobs/:id" element={<JobPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(await screen.findByLabelText('Review tkt_0005')).toBeInTheDocument();
  expect(screen.getByText('Extracting tickets…')).toBeInTheDocument();
  expect(screen.queryByText('Processing complete')).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getByText('Processing complete')).toBeInTheDocument(), {
    timeout: 2000,
  });
  expect(api.job).toHaveBeenCalledTimes(2);
  expect(api.results).toHaveBeenCalledTimes(2);
});
