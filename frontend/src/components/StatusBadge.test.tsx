import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { COMPLAINT_STATUSES, type ComplaintStatus } from '../lib/complaintStatus';
import { StatusBadge } from './StatusBadge';

// docs/05_UI_SPEC.md §1 - citizen label, colour token and icon for every status.
const SPEC: Record<ComplaintStatus, { label: string; tone: string; icon: string }> = {
  SUBMITTED: { label: 'Received', tone: 'neutral', icon: 'inbox' },
  VERIFIED: { label: 'Under review', tone: 'neutral', icon: 'search' },
  SCHEDULED: { label: 'Planned', tone: 'info', icon: 'calendar' },
  ASSIGNED: { label: 'Contractor assigned', tone: 'info', icon: 'user-check' },
  INSPECTED: { label: 'Site inspected', tone: 'info', icon: 'clipboard' },
  IN_PROGRESS: { label: 'Work in progress', tone: 'warning', icon: 'hammer' },
  COMPLETED: { label: 'Work completed — please confirm', tone: 'success', icon: 'check' },
  CLOSED: { label: 'Closed', tone: 'success', icon: 'check-double' },
  REOPENED: { label: 'Reopened', tone: 'warning', icon: 'rotate' },
  REJECTED: { label: 'Not accepted', tone: 'danger', icon: 'x' },
  MERGED: { label: 'Linked to CB-000123', tone: 'neutral', icon: 'link' },
};

describe('StatusBadge', () => {
  it('knows exactly the 11 statuses of the database CHECK', () => {
    expect([...COMPLAINT_STATUSES].sort()).toEqual(Object.keys(SPEC).sort());
  });

  it.each(COMPLAINT_STATUSES)('%s shows its label text and an icon, not colour only', (status) => {
    render(<StatusBadge status={status} mergedIntoPublicRef="CB-000123" />);

    const badge = screen.getByTestId('status-badge');
    expect(badge).toHaveTextContent(SPEC[status].label);
    expect(badge).toHaveAttribute('data-status', status);
    expect(badge).toHaveAttribute('data-tone', SPEC[status].tone);

    const icon = badge.querySelector('svg');
    expect(icon).not.toBeNull();
    expect(icon).toHaveAttribute('data-icon', SPEC[status].icon);
    expect(icon).toHaveAttribute('aria-hidden', 'true');
  });

  it('MERGED without a master reference still says it is linked', () => {
    render(<StatusBadge status="MERGED" />);
    expect(screen.getByTestId('status-badge')).toHaveTextContent('Linked to another complaint');
  });
});
