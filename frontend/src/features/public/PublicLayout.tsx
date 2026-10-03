import { Outlet } from 'react-router';
import { PublicShell } from './PublicShell';

export function PublicLayout() {
  return (
    <PublicShell>
      <Outlet />
    </PublicShell>
  );
}
