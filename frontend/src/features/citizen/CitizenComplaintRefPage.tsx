import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Navigate, useParams } from 'react-router';
import { CITIZEN_COMPLAINTS_KEY, findOwnComplaintId } from '../../api/citizenComplaints';
import { ErrorState } from '../../components/ErrorState';
import { PageSkeleton } from '../../components/PageSkeleton';
import { ComplaintNotFound } from './complaints/ComplaintNotFound';

const PUBLIC_REF = /^CB-\d{6,}$/;

/**
 * `/citizen/complaints/ref/CB-000123` - where the `/c/:publicRef` track link of e-mails and WhatsApp lands after login.
 * Opens the citizen's complaint with that number; a merged report's owner gets the master's messages, so otherwise
 * the citizen's own complaint linked to it opens. Anything else: a friendly not-found page.
 */
export function CitizenComplaintRefPage() {
  const { t } = useTranslation();
  const { publicRef = '' } = useParams();
  const valid = PUBLIC_REF.test(publicRef);
  const lookup = useQuery({
    queryKey: [...CITIZEN_COMPLAINTS_KEY, 'ref', publicRef, 'follow-merged'],
    queryFn: ({ signal }) => findOwnComplaintId(publicRef, { followMerged: true, signal }),
    enabled: valid,
  });

  if (valid && typeof lookup.data === 'number') return <Navigate to={`/citizen/complaints/${lookup.data}`} replace />;
  if (valid && lookup.isError) return <ErrorState error={lookup.error} onRetry={() => void lookup.refetch()} />;
  if (valid && lookup.isPending) {
    return (
      <div className="flex flex-col gap-3">
        <p className="font-medium text-slate-700">{t('trackRef.searching', { publicRef })}</p>
        <PageSkeleton rows={2} />
      </div>
    );
  }
  return <ComplaintNotFound title={t('trackRef.notFoundTitle', { publicRef })} text={t('trackRef.notFoundText')} />;
}
