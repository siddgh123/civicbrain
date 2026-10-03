import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { MessageCard, actionClass } from './MessageCard';

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <MessageCard
      title={t('errorPages.notFoundTitle')}
      text={t('errorPages.notFoundText')}
      action={
        <Link to="/" className={actionClass}>
          {t('common.goHome')}
        </Link>
      }
    />
  );
}
