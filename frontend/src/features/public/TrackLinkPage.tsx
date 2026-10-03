import { Navigate, useParams } from 'react-router';
import { homePathForRole } from '../../auth/authContext';
import { useAuth } from '../../auth/useAuth';
import { NotFoundPage } from './NotFoundPage';

const PUBLIC_REF = /^CB-\d{6,}$/;

/**
 * `/c/CB-000123` - the track link in e-mail/WhatsApp messages. Behind RequireAuth (login first, then back here);
 * a citizen goes on to the complaint, other roles to their start page. P11 builds the detail screen.
 */
export function TrackLinkPage() {
  const { publicRef = '' } = useParams();
  const { user } = useAuth();
  if (!PUBLIC_REF.test(publicRef)) return <NotFoundPage />;
  if (user?.role !== 'CITIZEN') return <Navigate to={user ? homePathForRole(user.role) : '/'} replace />;
  return <Navigate to={`/citizen/complaints/ref/${publicRef}`} replace />;
}
