import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RecordEditor } from '../components/RecordEditor';
import { ApiError, api } from '../lib/api';
import { makeRecord } from './fixtures';

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>();
  return { ...actual, api: { ...actual.api, patch: vi.fn() } };
});

beforeEach(() => vi.clearAllMocks());

describe('Human review', () => {
  it('shows server validation errors next to their field and keeps the draft', async () => {
    vi.mocked(api.patch).mockRejectedValue(
      new ApiError('Check fields', { company: 'Company is required' }, 422),
    );
    const user = userEvent.setup();
    render(<RecordEditor record={makeRecord()} onSaved={vi.fn()} />);
    await user.clear(screen.getByLabelText('Company'));
    await user.click(screen.getByRole('button', { name: /Save changes/ }));
    expect(await screen.findByText('Company is required')).toBeInTheDocument();
    expect(screen.getByLabelText('Company')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Company')).toHaveValue('');
  });

  it('sends only changed fields and preserves numeric amounts and boolean false', async () => {
    const user = userEvent.setup();
    const record = makeRecord();
    const updated = makeRecord({ version: 2, reviewed: true });
    const saved = vi.fn();
    vi.mocked(api.patch).mockResolvedValue(updated);
    render(<RecordEditor record={record} onSaved={saved} />);
    await user.type(screen.getByLabelText('Refund amount (USD)'), '300');
    await user.click(screen.getByRole('button', { name: /Approve & save/ }));
    await waitFor(() => expect(saved).toHaveBeenCalledWith(updated));
    expect(api.patch).toHaveBeenCalledWith(record, { refund_amount: 300 }, true);
    expect(screen.getByLabelText('Escalated')).toHaveValue('false');
  });

  it('preserves unsaved input when polling delivers another record snapshot', async () => {
    const user = userEvent.setup();
    const original = makeRecord();
    const saved = vi.fn();
    const view = render(<RecordEditor record={original} onSaved={saved} />);
    await user.clear(screen.getByLabelText('Company'));
    await user.type(screen.getByLabelText('Company'), 'My draft');
    view.rerender(<RecordEditor record={{ ...original }} onSaved={saved} />);
    expect(screen.getByLabelText('Company')).toHaveValue('My draft');
    view.rerender(<RecordEditor record={makeRecord({ version: 2 })} onSaved={saved} />);
    expect(screen.getByLabelText('Company')).toHaveValue('My draft');
    expect(screen.getByText(/A newer version is available/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save changes/ })).toBeDisabled();
  });

  it('marks saved fields as human edited and enables reviewed state', async () => {
    const record = makeRecord();
    const updated = makeRecord({
      version: 2,
      reviewed: true,
      status: 'done',
      values: { ...record.values, company: 'Acme Ltd' },
      field_meta: {
        ...record.field_meta,
        company: { source: 'human', grounding: 'grounded', evidence: null },
      },
    });
    vi.mocked(api.patch).mockResolvedValue(updated);
    const user = userEvent.setup();
    render(<RecordEditor record={record} onSaved={vi.fn()} />);
    await user.clear(screen.getByLabelText('Company'));
    await user.type(screen.getByLabelText('Company'), 'Acme Ltd');
    await user.click(screen.getByRole('button', { name: /Approve & save/ }));
    expect(await screen.findByText('Human edited')).toBeInTheDocument();
    expect(screen.getByText('reviewed')).toBeInTheDocument();
  });
});
