import type { ReactNode } from 'react';
import { ForbiddenPage } from '../features/public/ForbiddenPage';
import { PublicShell } from '../features/public/PublicShell';
import type { Role } from './authContext';
import { RequireAuth } from './RequireAuth';
import { useAuth } from './useAuth';

interface RequireRoleProps {
  roles: readonly Role[];
  children: ReactNode;
  /** Inside a portal layout (e.g. /officer/admin) the "No access" message goes without its own page frame. */
  inLayout?: boolean;
}

/** UX guard only - the server enforces every rule. Signed out -> login; wrong role -> "No access" page. */
export function RequireRole({ roles, children, inLayout = false }: RequireRoleProps) {
  return (
    <RequireAuth>
      <RoleCheck roles={roles} inLayout={inLayout}>
        {children}
      </RoleCheck>
    </RequireAuth>
  );
}

function RoleCheck({ roles, children, inLayout }: RequireRoleProps) {
  const { user } = useAuth();
  if (user !== null && roles.includes(user.role)) return children;
  if (inLayout) return <ForbiddenPage />;
  return (
    <PublicShell>
      <ForbiddenPage />
    </PublicShell>
  );
}
