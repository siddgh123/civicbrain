import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import { useAuth } from './useAuth';

/** UX guard only - the server enforces every rule. Signed out -> /login?returnTo=<this page>. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null) {
    const returnTo = `${location.pathname}${location.search}`;
    return <Navigate to={`/login?${new URLSearchParams({ returnTo }).toString()}`} replace />;
  }
  return children;
}
