import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { homePathForRole } from '../../auth/authContext';
import { useAuth } from '../../auth/useAuth';
import { MessageCard, actionClass } from './MessageCard';

/** Signed in, but this page is for another role (UX only; the API answers 403/404 anyway). */
export function ForbiddenPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  return (
    <MessageCard
      title={t('errorPages.forbiddenTitle')}
      text={t('errorPages.forbiddenText')}
      action={
        <Link to={user ? homePathForRole(user.role) : '/'} className={actionClass}>
          {t('errorPages.goToMyPortal')}
        </Link>
      }
    />
  );
}
