import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { CITIZEN_COMPLAINTS_KEY, citizenApi, findOwnComplaintId, type ComplaintDetail } from '../../../api/citizenComplaints';
import { ErrorState } from '../../../components/ErrorState';
import { linkClass } from '../../../components/form/fields';
import { LinkIcon } from '../../../components/icons/icons';
import { PageSkeleton } from '../../../components/PageSkeleton';
import { ProtectedImage } from '../../../components/ProtectedImage';
import { StatusBadge } from '../../../components/StatusBadge';
import { Timeline } from '../../../components/Timeline';
import { ApiError } from '../../../lib/api';
import { formatDate, formatDateTime } from '../../../lib/format';
import { ComplaintNotFound } from './ComplaintNotFound';

const PHOTO_ROLES = ['CITIZEN_EVIDENCE', 'INSPECTION', 'WORK_IN_PROGRESS', 'COMPLETION_PROOF'] as const;
type PhotoRole = (typeof PHOTO_ROLES)[number];

function isPhotoRole(role: string): role is PhotoRole {
  return (PHOTO_ROLES as readonly string[]).includes(role);
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="font-semibold text-slate-900">{title}</h2>
      {children}
    </section>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-slate-600">{label}</dt>
      <dd className="break-words whitespace-pre-line text-slate-900">{children}</dd>
    </>
  );
}

/** "Linked to CB-…": the master opens only when it is one of the citizen's own complaints (others are 404, 04 §5). */
function MergedNotice({ masterRef }: { masterRef: string }) {
  const { t } = useTranslation();
  const own = useQuery({
    queryKey: [...CITIZEN_COMPLAINTS_KEY, 'ref', masterRef, 'exact'],
    queryFn: ({ signal }) => findOwnComplaintId(masterRef, { followMerged: false, signal }),
  });
  return (
    <div
      data-testid="merged-notice"
      className="flex items-start gap-3 rounded-xl border border-status-info-border bg-status-info-bg p-4 text-status-info-fg"
    >
      <LinkIcon className="mt-0.5 size-5 shrink-0" />
      <div className="flex flex-col gap-1">
        <p className="font-bold">{t('status.MERGED', { publicRef: masterRef })}</p>
        <p>{t('complaintDetail.linkedText')}</p>
        {typeof own.data === 'number' && (
          <Link to={`/citizen/complaints/${own.data}`} className={linkClass}>
            {t('complaintDetail.openLinked', { publicRef: masterRef })}
          </Link>
        )}
      </div>
    </div>
  );
}

function photoLabel(t: ReturnType<typeof useTranslation>['t'], role: string): string {
  return isPhotoRole(role) ? t(`complaintDetail.photoRole.${role}`) : t('complaintDetail.photos');
}

function Detail({ complaint }: { complaint: ComplaintDetail }) {
  const { t } = useTranslation();
  const hasWork = complaint.contractorName !== null || complaint.plannedDate !== null;
  return (
    <>
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-slate-600 tabular-nums">{complaint.publicRef}</p>
        <h1 className="text-2xl font-bold break-words text-slate-900">{complaint.title}</h1>
        <div>
          <StatusBadge status={complaint.status} mergedIntoPublicRef={complaint.mergedIntoPublicRef} />
        </div>
      </div>

      {complaint.status === 'MERGED' && complaint.mergedIntoPublicRef !== null && (
        <MergedNotice masterRef={complaint.mergedIntoPublicRef} />
      )}

      {complaint.images.length > 0 && (
        <Section title={t('complaintDetail.photos')}>
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {complaint.images.map((image) => (
              <li key={image.imageId}>
                <figure className="flex flex-col gap-1.5">
                  <ProtectedImage
                    imageId={image.imageId}
                    alt={photoLabel(t, image.role)}
                    className="aspect-[4/3] w-full rounded-lg bg-slate-100 object-cover"
                  />
                  <figcaption aria-hidden="true" className="text-sm text-slate-600">
                    {photoLabel(t, image.role)}
                  </figcaption>
                </figure>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {hasWork && (
        <Section title={t('complaintDetail.work')}>
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
            {complaint.contractorName !== null && (
              <Fact label={t('complaintDetail.contractor')}>{complaint.contractorName}</Fact>
            )}
            {complaint.plannedDate !== null && (
              <Fact label={t('complaintDetail.plannedDate')}>{formatDate(complaint.plannedDate)}</Fact>
            )}
          </dl>
        </Section>
      )}

      <Section title={t('complaintDetail.details')}>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2">
          {complaint.categoryName !== null && <Fact label={t('complaintDetail.category')}>{complaint.categoryName}</Fact>}
          {complaint.wardNumber !== null && <Fact label={t('complaintDetail.ward')}>{complaint.wardNumber}</Fact>}
          <Fact label={t('complaintDetail.submittedAt')}>{formatDateTime(complaint.submittedAt)}</Fact>
          {complaint.landmark !== null && <Fact label={t('complaintDetail.landmark')}>{complaint.landmark}</Fact>}
          <Fact label={t('complaintDetail.description')}>{complaint.description}</Fact>
        </dl>
      </Section>

      <Section title={t('complaintDetail.timeline')}>
        <Timeline
          entries={complaint.timeline}
          label={t('complaintDetail.timeline')}
          mergedIntoPublicRef={complaint.mergedIntoPublicRef}
        />
      </Section>
    </>
  );
}

/**
 * `/citizen/complaints/:id` (docs/05_UI_SPEC.md §4.7, FR-13/FR-15): photos, status timeline newest first with
 * remarks, contractor + planned date when assigned, MERGED → "Linked to CB-…". Not the citizen's (or missing) → a
 * friendly not-found page (the API answers 404 for both). Feedback buttons come with P22.
 */
export function ComplaintDetailPage() {
  const { t } = useTranslation();
  const { id = '' } = useParams();
  const complaintId = /^\d+$/.test(id) ? Number(id) : null;
  const detail = useQuery({
    queryKey: [...CITIZEN_COMPLAINTS_KEY, 'detail', complaintId],
    queryFn: ({ signal }) => citizenApi.detail(complaintId ?? 0, signal),
    enabled: complaintId !== null,
  });
  const notFound = complaintId === null || (detail.error instanceof ApiError && detail.error.code === 'NOT_FOUND');

  return (
    <article className="flex flex-col gap-4">
      <Link to="/citizen/complaints" className={`${linkClass} self-start text-sm`}>
        ← {t('complaintDetail.back')}
      </Link>
      {notFound ? (
        <ComplaintNotFound title={t('complaintDetail.notFoundTitle')} text={t('complaintDetail.notFoundText')} />
      ) : detail.isPending ? (
        <PageSkeleton rows={4} />
      ) : detail.isError ? (
        <ErrorState error={detail.error} onRetry={() => void detail.refetch()} />
      ) : (
        <Detail complaint={detail.data} />
      )}
    </article>
  );
}
