import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import { PageSkeleton } from '../components/PageSkeleton';
import { useAuth } from './useAuth';

interface RequireAuthProps {
  children: ReactNode;
  /** Only the change-password screen itself is open while `mustChangePassword` is set. */
  allowPasswordChange?: boolean;
}

/**
 * UX guard only - the server enforces every rule. While the silent refresh runs: skeleton. Signed out ->
 * /login?returnTo=<this page>. One-time password -> /change-password first (PASSWORD_CHANGE_REQUIRED, docs/12 §2).
 */
export function RequireAuth({ children, allowPasswordChange = false }: RequireAuthProps) {
  const { status, user } = useAuth();
  const location = useLocation();
  if (status === 'loading') {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-8">
        <PageSkeleton rows={3} />
      </div>
    );
  }
  if (user === null) {
    const returnTo = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?${new URLSearchParams({ returnTo }).toString()}`} replace />;
  }
  if (user.mustChangePassword && !allowPasswordChange) return <Navigate to="/change-password" replace />;
  return children;
}
