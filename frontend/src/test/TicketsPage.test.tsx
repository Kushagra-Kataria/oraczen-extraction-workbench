import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import { TicketsPage } from '../views/TicketsPage';
import { ticket } from './fixtures';

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));

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
  render(<TicketsPage />);
  const user = userEvent.setup();
  await screen.findByText('Search bug');
  await user.type(screen.getByLabelText('Search tickets'), 'apostrophe');
  expect(screen.queryByText('URGENT: platform unavailable')).not.toBeInTheDocument();
  await user.click(screen.getByLabelText('Select all filtered tickets'));
  await user.click(screen.getByRole('button', { name: /Extract 1 ticket/ }));
  await waitFor(() => expect(api.start).toHaveBeenCalledWith(['tkt_0003']));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/jobs/created'));
});

it('can select the complete source batch', async () => {
  vi.mocked(api.tickets).mockResolvedValue({
    tickets: [ticket, { ...ticket, id: 'tkt_0003', subject: 'Search bug' }],
  });
  vi.mocked(api.start).mockResolvedValue({ id: 'all-tickets' } as Awaited<
    ReturnType<typeof api.start>
  >);
  render(<TicketsPage />);
  const user = userEvent.setup();
  await screen.findByText('Search bug');
  await user.click(screen.getByRole('button', { name: 'Select all 2 tickets →' }));
  await user.click(screen.getByRole('button', { name: /Extract 2 tickets/ }));
  await waitFor(() => expect(api.start).toHaveBeenCalledWith([ticket.id, 'tkt_0003']));
});

it('previews the full source without extracting or losing the inbox selection', async () => {
  // jsdom has no native dialog implementation; browser checks cover focus and Escape.
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value(this: HTMLDialogElement) {
        this.setAttribute('open', '');
      },
    },
    close: {
      configurable: true,
      value(this: HTMLDialogElement) {
        this.removeAttribute('open');
        this.dispatchEvent(new Event('close'));
      },
    },
  });
  const body = `${'A long quoted conversation. '.repeat(15)}\nFinal line beyond the inbox excerpt.`;
  vi.mocked(api.tickets).mockResolvedValue({ tickets: [{ ...ticket, body, attachments: 2 }] });
  render(<TicketsPage />);
  const user = userEvent.setup();
  await screen.findByText(ticket.subject);
  await user.click(screen.getByLabelText(`Select ${ticket.id}`));
  const viewButton = screen.getByRole('button', { name: `View ticket ${ticket.id}` });
  await user.click(viewButton);
  const preview = screen.getByRole('dialog', { name: ticket.subject });
  expect(within(preview).getByText(/Final line beyond the inbox excerpt/).textContent).toBe(body);
  expect(within(preview).getByText(ticket.from_email)).toBeInTheDocument();
  expect(within(preview).getByText('2 (count only; files are not supplied)')).toBeInTheDocument();
  expect(api.start).not.toHaveBeenCalled();
  await user.click(within(preview).getByRole('button', { name: 'Close' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByLabelText(`Select ${ticket.id}`)).toBeChecked();
  expect(screen.getByRole('button', { name: /Extract 1 ticket/ })).toBeEnabled();
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal');
  Reflect.deleteProperty(HTMLDialogElement.prototype, 'close');
});
