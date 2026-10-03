import type { RouteObject } from 'react-router';
import type { Role } from '../auth/authContext';
import { RequireAuth } from '../auth/RequireAuth';
import { RequireRole } from '../auth/RequireRole';
import { ChangePasswordPage } from '../features/auth/ChangePasswordPage';
import { LoginPage } from '../features/auth/LoginPage';
import { OtpPage } from '../features/auth/OtpPage';
import { RegisterPage } from '../features/auth/RegisterPage';
import { CitizenComplaintRefPage } from '../features/citizen/CitizenComplaintRefPage';
import { CitizenHomePage } from '../features/citizen/CitizenHomePage';
import { CitizenLayout } from '../features/citizen/CitizenLayout';
import { NewComplaintPage } from '../features/citizen/NewComplaintPage';
import { ProfilePage } from '../features/citizen/ProfilePage';
import { ContractorLayout } from '../features/contractor/ContractorLayout';
import { OfficerLayout } from '../features/officer/OfficerLayout';
import { LandingPage } from '../features/public/LandingPage';
import { NotFoundPage } from '../features/public/NotFoundPage';
import { PrivacyPage } from '../features/public/PrivacyPage';
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
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'verify-email', element: <OtpPage /> },
      { path: 'privacy', element: <PrivacyPage /> },
      {
        path: 'change-password',
        element: (
          <RequireAuth allowPasswordChange>
            <ChangePasswordPage />
          </RequireAuth>
        ),
      },
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
      { index: true, element: <CitizenHomePage /> }, // recent complaints list: P11
      { path: 'new', element: <NewComplaintPage /> }, // photo step (CameraCapture); full wizard: P11
      { path: 'profile', element: <ProfilePage /> },
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
