import type { RouteObject } from 'react-router';
import type { Role } from '../auth/authContext';
import { RequireAuth } from '../auth/RequireAuth';
import { RequireRole } from '../auth/RequireRole';
import { CitizenComplaintRefPage } from '../features/citizen/CitizenComplaintRefPage';
import { CitizenLayout } from '../features/citizen/CitizenLayout';
import { ContractorLayout } from '../features/contractor/ContractorLayout';
import { OfficerLayout } from '../features/officer/OfficerLayout';
import { LandingPage } from '../features/public/LandingPage';
import { NotFoundPage } from '../features/public/NotFoundPage';
import { PublicLayout } from '../features/public/PublicLayout';
import { RouteErrorPage } from '../features/public/RouteErrorPage';
import { TrackLinkPage } from '../features/public/TrackLinkPage';
import { TranslatedPlaceholder as Placeholder } from './TranslatedPlaceholder';

const CITIZEN: readonly Role[] = ['CITIZEN'];
const OFFICER: readonly Role[] = ['OFFICER', 'ADMIN'];
const ADMIN: readonly Role[] = ['ADMIN'];
const CONTRACTOR: readonly Role[] = ['CONTRACTOR', 'CONTRACTOR_STAFF'];

// One app, three portals (docs/05_UI_SPEC.md). Guards are UX only - the server enforces every rule.
// Each portal has its own errorElement (docs/12_ERROR_HANDLING.md §6). Screens marked Placeholder come in later prompts.
export const routes: RouteObject[] = [
  {
    element: <PublicLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <LandingPage /> },
      { path: 'login', element: <Placeholder titleKey="pages.login" /> }, // P07
      { path: 'register', element: <Placeholder titleKey="pages.register" /> }, // P07
      { path: 'privacy', element: <Placeholder titleKey="pages.privacy" /> }, // P07 (GET /public/privacy-notice)
      {
        path: 'c/:publicRef',
        element: (
          <RequireAuth>
            <TrackLinkPage />
          </RequireAuth>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    path: 'citizen',
    element: (
      <RequireRole roles={CITIZEN}>
        <CitizenLayout />
      </RequireRole>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Placeholder titleKey="pages.citizenHome" /> }, // P11
      { path: 'new', element: <Placeholder titleKey="pages.citizenNew" /> }, // P11
      { path: 'complaints', element: <Placeholder titleKey="pages.citizenComplaints" /> }, // P11
      { path: 'complaints/ref/:publicRef', element: <CitizenComplaintRefPage /> }, // P11
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    path: 'officer',
    element: (
      <RequireRole roles={OFFICER}>
        <OfficerLayout />
      </RequireRole>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Placeholder titleKey="pages.officerDashboard" /> }, // P15
      { path: 'complaints', element: <Placeholder titleKey="pages.officerComplaints" /> }, // P15
      { path: 'plans', element: <Placeholder titleKey="pages.officerPlans" /> }, // P19
      { path: 'contractors', element: <Placeholder titleKey="pages.officerContractors" /> }, // P15
      {
        path: 'admin',
        element: (
          <RequireRole roles={ADMIN} inLayout>
            <Placeholder titleKey="pages.officerAdmin" />
          </RequireRole>
        ),
      }, // P15
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    path: 'contractor',
    element: (
      <RequireRole roles={CONTRACTOR}>
        <ContractorLayout />
      </RequireRole>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Placeholder titleKey="pages.contractorToday" /> }, // P22
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];
