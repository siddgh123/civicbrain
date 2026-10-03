import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { PRIVACY_NOTICE_QUERY_KEY, publicApi } from '../../api/publicApi';
import { PrivacyNoticeBox } from '../auth/PrivacyNoticeBox';

/** The current versioned privacy notice (GET /public/privacy-notice, FR-60, docs/07_SECURITY.md §7). */
export function PrivacyPage() {
  const { t } = useTranslation();
  const notice = useQuery({ queryKey: PRIVACY_NOTICE_QUERY_KEY, queryFn: publicApi.privacyNotice });
  return (
    <section className="mx-auto flex max-w-2xl flex-col gap-4">
      <h1 className="text-2xl font-bold text-slate-900">{t('pages.privacy')}</h1>
      <PrivacyNoticeBox query={notice} tall />
    </section>
  );
}
