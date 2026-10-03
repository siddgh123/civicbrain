import type { UseQueryResult } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { PrivacyNotice } from '../../api/publicApi';
import { ErrorState } from '../../components/ErrorState';
import { formatDateTime } from '../../lib/format';

/** The current notice (GET /public/privacy-notice) in a keyboard-scrollable box with its version (05 §3, 07 §7). */
export function PrivacyNoticeBox({ query, tall = false }: { query: UseQueryResult<PrivacyNotice>; tall?: boolean }) {
  const { t } = useTranslation();
  if (query.isPending) {
    return (
      <div role="status" aria-busy="true" aria-label={t('common.loading')} className="flex flex-col gap-2 rounded-lg border border-slate-200 p-4">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-4 rounded bg-slate-200 motion-safe:animate-pulse" />
        ))}
      </div>
    );
  }
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const notice = query.data;
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-sm text-slate-600">
        {t('auth.privacyVersion', { version: notice.version })} · {formatDateTime(notice.publishedAt)}
      </p>
      <div
        role="region"
        aria-label={t('auth.privacyRegion')}
        tabIndex={0}
        data-testid="privacy-notice"
        className={`overflow-y-auto rounded-lg border border-slate-300 bg-slate-50 p-4 text-sm leading-relaxed whitespace-pre-line text-slate-800 ${tall ? '' : 'max-h-44'}`}
      >
        {notice.summary}
      </div>
    </div>
  );
}
