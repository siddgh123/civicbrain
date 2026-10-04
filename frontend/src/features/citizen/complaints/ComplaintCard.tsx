import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import type { ComplaintListItem } from '../../../api/citizenComplaints';
import { ProtectedImage } from '../../../components/ProtectedImage';
import { StatusBadge } from '../../../components/StatusBadge';
import { formatDateTime } from '../../../lib/format';
import { CategoryIcon } from '../wizard/CategoryIcon';

/** One of the citizen's complaints in a list (home, My complaints): the whole card opens the detail. */
export function ComplaintCard({ complaint }: { complaint: ComplaintListItem }) {
  const { t } = useTranslation();
  return (
    <Link
      to={`/citizen/complaints/${complaint.complaintId}`}
      data-testid="complaint-card"
      className="flex gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm hover:border-brand-600 hover:bg-brand-50/40"
    >
      {complaint.thumbnailImageId !== null ? (
        <ProtectedImage
          imageId={complaint.thumbnailImageId}
          alt={t('complaints.photoOf', { publicRef: complaint.publicRef })}
          className="size-16 shrink-0 rounded-lg object-cover"
        />
      ) : (
        <span className="grid size-16 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-700">
          <CategoryIcon name={complaint.categoryName ?? ''} className="size-7" />
        </span>
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p className="font-semibold break-words text-slate-900">{complaint.title}</p>
        <p className="text-sm text-slate-600">
          <span className="font-medium tabular-nums">{complaint.publicRef}</span>
          {complaint.categoryName !== null && ` · ${complaint.categoryName}`}
          {complaint.wardNumber !== null && ` · ${t('complaints.ward', { ward: complaint.wardNumber })}`}
        </p>
        <div>
          <StatusBadge status={complaint.status} />
        </div>
        <p className="text-xs text-slate-500">{t('complaints.submitted', { date: formatDateTime(complaint.submittedAt) })}</p>
      </div>
    </Link>
  );
}
