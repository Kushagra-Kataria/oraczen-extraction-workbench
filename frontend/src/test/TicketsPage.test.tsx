import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { TicketsPage } from '../pages/TicketsPage';
import { ticket } from './fixtures';

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>();
  return { ...actual, api: { ...actual.api, tickets: vi.fn(), start: vi.fn() } };
});

beforeEach(() => vi.clearAllMocks());

it('filters tickets and submits only the selected IDs before navigating to the job', async () => {
  vi.mocked(api.tickets).mockResolvedValue({
    tickets: [
      ticket,
      { ...ticket, id: 'tkt_0003', subject: 'Search bug', body: 'An apostrophe breaks search.' },
    ],
  });
  vi.mocked(api.start).mockResolvedValue({ id: 'created' } as Awaited<
    ReturnType<typeof api.start>
  >);
  render(
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<TicketsPage />} />
        <Route path="/jobs/:id" element={<p>Job opened</p>} />
      </Routes>
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await screen.findByText('Search bug');
  await user.type(screen.getByLabelText('Search tickets'), 'apostrophe');
  expect(screen.queryByText('URGENT: platform unavailable')).not.toBeInTheDocument();
  await user.click(screen.getByLabelText('Select all filtered tickets'));
  await user.click(screen.getByRole('button', { name: /Extract 1 ticket/ }));
  await waitFor(() => expect(api.start).toHaveBeenCalledWith(['tkt_0003']));
  expect(await screen.findByText('Job opened')).toBeInTheDocument();
});

it('can select the complete source batch without relying on the review demo', async () => {
  vi.mocked(api.tickets).mockResolvedValue({
    tickets: [ticket, { ...ticket, id: 'tkt_0003', subject: 'Search bug' }],
  });
  vi.mocked(api.start).mockResolvedValue({ id: 'all-tickets' } as Awaited<
    ReturnType<typeof api.start>
  >);
  render(
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<TicketsPage />} />
        <Route path="/jobs/:id" element={<p>Job opened</p>} />
      </Routes>
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await screen.findByText('Search bug');
  await user.click(screen.getByRole('button', { name: 'Select all 2 tickets →' }));
  await user.click(screen.getByRole('button', { name: /Extract 2 tickets/ }));
  await waitFor(() => expect(api.start).toHaveBeenCalledWith([ticket.id, 'tkt_0003']));
});
