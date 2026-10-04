import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import type { ComplaintDetail, ComplaintListItem } from '../../../api/citizenComplaints';
import { installObjectUrls } from '../../../test/browserFakes';
import { problem, renderApp, signedIn } from '../../../test/renderApp';
import { server } from '../../../test/server';

// Requirement: FR-13 (own complaints: list, detail, timeline), FR-15 (contractor name, "Linked to CB-…");
// docs/05 §1 (StatusBadge), §2 (four states), §4.1/§4.6/§4.7; docs/04 §5; prompt P11 Build 2-3.

function item(overrides: Partial<ComplaintListItem> = {}): ComplaintListItem {
  return {
    complaintId: 41,
    publicRef: 'CB-000041',
    title: 'Deep pothole near bus stop',
    categoryName: 'Pothole',
    status: 'VERIFIED',
    wardNumber: 7,
    submittedAt: '2026-10-03T08:20:00+05:30',
    thumbnailImageId: null,
    ...overrides,
  };
}

function detail(overrides: Partial<ComplaintDetail> = {}): ComplaintDetail {
  return {
    ...item(),
    categoryId: 1,
    description: 'A deep pothole in the left lane.',
    landmark: 'Bus stop',
    latitude: 18.744,
    longitude: 73.676,
    images: [],
    timeline: [{ status: 'SUBMITTED', at: '2026-10-03T08:20:00+05:30', remarks: null }],
    contractorName: null,
    plannedDate: null,
    mergedIntoPublicRef: null,
    canGiveFeedback: false,
    ...overrides,
  };
}

function page(items: ComplaintListItem[]) {
  return { items, page: 0, size: 100, totalItems: items.length, totalPages: items.length === 0 ? 0 : 1 };
}

function mockList(items: ComplaintListItem[]) {
  server.use(http.get('/api/v1/citizen/complaints', () => HttpResponse.json(page(items))));
}

function mockDetails(details: ComplaintDetail[]) {
  server.use(
    http.get('/api/v1/citizen/complaints/:id', ({ params }) => {
      const found = details.find((d) => String(d.complaintId) === params.id);
      return found ? HttpResponse.json(found) : problem(404, 'NOT_FOUND');
    }),
  );
}

const citizen = signedIn('CITIZEN');

describe('My complaints list', () => {
  it('a new account sees the empty state with the Report action', async () => {
    mockList([]);
    renderApp('/citizen/complaints', { auth: citizen });

    expect(await screen.findByText('You have not reported a problem yet.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Report a problem' })).toHaveAttribute('href', '/citizen/new');
    expect(screen.queryByRole('button', { name: 'Open' })).not.toBeInTheDocument();
  });

  it('shows a skeleton while loading, then Open / Closed chips that filter the list', async () => {
    mockList([
      item({ complaintId: 1, publicRef: 'CB-000001', title: 'Open pothole', status: 'ASSIGNED' }),
      item({ complaintId: 2, publicRef: 'CB-000002', title: 'Fixed garbage', status: 'CLOSED' }),
      item({ complaintId: 3, publicRef: 'CB-000003', title: 'Rejected one', status: 'REJECTED' }),
      item({ complaintId: 4, publicRef: 'CB-000004', title: 'Merged one', status: 'MERGED' }),
    ]);
    const { user } = renderApp('/citizen/complaints', { auth: citizen });

    expect(screen.getByRole('status', { name: 'Loading…' })).toBeInTheDocument();
    const list = await screen.findByRole('list', { name: 'My complaints' });
    expect(within(list).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual([
      '/citizen/complaints/1',
      '/citizen/complaints/4',
    ]);
    expect(screen.getByRole('button', { name: 'Open' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(list).getByText('Contractor assigned')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Closed' }));
    const closed = screen.getByRole('list', { name: 'My complaints' });
    expect(within(closed).getAllByRole('link').map((a) => a.textContent)).toEqual([
      expect.stringContaining('Fixed garbage'),
      expect.stringContaining('Rejected one'),
    ]);
  });

  it('an error shows the message, the reference and Try again', async () => {
    // a 4xx is not retried (05 §2), so the error shows at once
    server.use(http.get('/api/v1/citizen/complaints', () => problem(403, 'FORBIDDEN', { requestId: 'req-9' })));
    renderApp('/citizen/complaints', { auth: citizen });

    expect(await screen.findByText("You don't have access to this.")).toBeInTheDocument();
    expect(screen.getByText('Reference: req-9')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});

describe('Citizen home', () => {
  it('shows the big Report button and the recent complaints with their status', async () => {
    mockList([item({ title: 'Deep pothole near bus stop', status: 'IN_PROGRESS' })]);
    renderApp('/citizen', { auth: citizen });

    expect(await screen.findByText('Deep pothole near bus stop')).toBeInTheDocument();
    expect(screen.getByText('Work in progress')).toBeInTheDocument();
    expect(screen.getByTestId('home-report')).toHaveAttribute('href', '/citizen/new');
    expect(screen.getByRole('link', { name: 'See all my complaints' })).toHaveAttribute('href', '/citizen/complaints');
  });
});

describe('Complaint detail', () => {
  it('MERGED shows "Linked to CB-…" with the explanation', async () => {
    mockList([item({ complaintId: 41, status: 'MERGED' })]);
    mockDetails([
      detail({
        status: 'MERGED',
        mergedIntoPublicRef: 'CB-000017',
        timeline: [
          { status: 'MERGED', at: '2026-10-03T08:21:00+05:30', remarks: 'Same pothole as an earlier report' },
          { status: 'SUBMITTED', at: '2026-10-03T08:20:00+05:30', remarks: null },
        ],
      }),
    ]);
    renderApp('/citizen/complaints/41', { auth: citizen });

    expect(await screen.findByRole('heading', { level: 1, name: 'Deep pothole near bus stop' })).toBeInTheDocument();
    const linked = screen.getByTestId('merged-notice');
    expect(within(linked).getByText('Linked to CB-000017')).toBeInTheDocument();
    expect(within(linked).getByText(/joined with an earlier report of the same problem/)).toBeInTheDocument();
    expect(screen.getAllByTestId('status-badge')[0]).toHaveTextContent('Linked to CB-000017');
  });

  it('"Linked to" opens the master when it is one of the citizen\'s own complaints', async () => {
    mockList([item({ complaintId: 41, status: 'MERGED' }), item({ complaintId: 17, publicRef: 'CB-000017' })]);
    mockDetails([detail({ status: 'MERGED', mergedIntoPublicRef: 'CB-000017' })]);
    renderApp('/citizen/complaints/41', { auth: citizen });

    expect(await screen.findByRole('link', { name: 'Open CB-000017' })).toHaveAttribute('href', '/citizen/complaints/17');
  });

  it('shows photos, the timeline newest first with remarks, contractor and planned date', async () => {
    installObjectUrls();
    mockList([]);
    server.use(
      http.get('/api/v1/files/:id', () => HttpResponse.arrayBuffer(new ArrayBuffer(4), { headers: { 'Content-Type': 'image/jpeg' } })),
    );
    mockDetails([
      detail({
        status: 'ASSIGNED',
        images: [{ imageId: 5, role: 'CITIZEN_EVIDENCE' }],
        contractorName: 'Shree Roads (prototype)',
        plannedDate: '2026-10-06',
        timeline: [
          { status: 'SUBMITTED', at: '2026-10-03T08:20:00+05:30', remarks: null },
          { status: 'ASSIGNED', at: '2026-10-04T10:00:00+05:30', remarks: 'Plan AP-1 assigned' },
          { status: 'VERIFIED', at: '2026-10-03T08:21:00+05:30', remarks: 'Checked automatically' },
        ],
      }),
    ]);
    renderApp('/citizen/complaints/41', { auth: citizen });

    expect(await screen.findByText('Shree Roads (prototype)')).toBeInTheDocument();
    expect(screen.getByText('6 Oct 2026')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Your photo' })).toBeInTheDocument();
    const timeline = screen.getByRole('list', { name: 'Progress' });
    const entries = within(timeline).getAllByRole('listitem');
    expect(entries.map((li) => li.querySelector('[data-status]')?.getAttribute('data-status'))).toEqual([
      'ASSIGNED',
      'VERIFIED',
      'SUBMITTED',
    ]);
    expect(within(entries[0]!).getByText('Plan AP-1 assigned')).toBeInTheDocument();
    expect(within(entries[0]!).getByText('4 Oct 2026, 10:00 am')).toBeInTheDocument();
  });

  it('another citizen\'s (or a missing) complaint shows a friendly not-found page', async () => {
    mockDetails([]);
    renderApp('/citizen/complaints/999', { auth: citizen });

    expect(await screen.findByRole('heading', { level: 1, name: 'Complaint not found' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to my complaints' })).toHaveAttribute('href', '/citizen/complaints');
  });
});

describe('Track link /c/:publicRef', () => {
  it('opens the matching complaint of the signed-in citizen', async () => {
    mockList([item({ complaintId: 8, publicRef: 'CB-000008' }), item({ complaintId: 41, publicRef: 'CB-000041' })]);
    mockDetails([detail({ complaintId: 41, publicRef: 'CB-000041' })]);
    const { router } = renderApp('/c/CB-000041', { auth: citizen });

    expect(await screen.findByRole('heading', { level: 1, name: 'Deep pothole near bus stop' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/citizen/complaints/41');
  });

  it('a master\'s track link opens the citizen\'s own complaint that is linked to it', async () => {
    mockList([item({ complaintId: 41, publicRef: 'CB-000041', status: 'MERGED' })]);
    mockDetails([detail({ complaintId: 41, status: 'MERGED', mergedIntoPublicRef: 'CB-000017' })]);
    const { router } = renderApp('/c/CB-000017', { auth: citizen });

    expect(await screen.findByTestId('merged-notice')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/citizen/complaints/41');
  });

  it('a reference that is not the citizen\'s shows a friendly 404', async () => {
    mockList([item()]);
    renderApp('/c/CB-000999', { auth: citizen });

    expect(await screen.findByRole('heading', { level: 1, name: 'Complaint CB-000999 not found' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to my complaints' })).toBeInTheDocument();
  });
});
