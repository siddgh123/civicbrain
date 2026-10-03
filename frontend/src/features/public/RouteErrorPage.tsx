import { useTranslation } from 'react-i18next';
import { MessageCard, actionClass } from './MessageCard';
import { PublicShell } from './PublicShell';

/**
 * Error boundary page of each portal (route `errorElement`, docs/12_ERROR_HANDLING.md §6): friendly text + Reload.
 * Reporting to POST /api/v1/client-errors comes when that endpoint exists.
 */
export function RouteErrorPage() {
  const { t } = useTranslation();
  return (
    <PublicShell>
      <MessageCard
        title={t('errorPages.crashTitle')}
        text={t('errorPages.crashText')}
        action={
          <button type="button" onClick={() => window.location.reload()} className={actionClass}>
            {t('common.reload')}
          </button>
        }
      />
    </PublicShell>
  );
}
