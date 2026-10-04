import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { CITIZEN_COMPLAINTS_KEY, citizenApi } from '../../api/citizenComplaints';
import { useAuth } from '../../auth/useAuth';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { linkClass } from '../../components/form/fields';
import { CameraIcon, UserCheckIcon } from '../../components/icons/icons';
import { PageSkeleton } from '../../components/PageSkeleton';
import { ComplaintCard } from './complaints/ComplaintCard';

const RECENT = 3;

/** docs/05_UI_SPEC.md §4.1 Home: big "Report a problem" button and the most recent complaints with their status. */
export function CitizenHomePage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const recent = useQuery({
    queryKey: [...CITIZEN_COMPLAINTS_KEY, 'recent'],
    queryFn: ({ signal }) => citizenApi.list(0, RECENT, signal),
  });
  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-4 rounded-2xl bg-brand-800 px-5 py-6 text-white shadow-sm">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold">{t('citizenHome.greeting', { name: user?.fullName ?? '' })}</h1>
          <p className="text-brand-50">{t('citizenHome.intro')}</p>
        </div>
        <Link
          to="/citizen/new"
          data-testid="home-report"
          className="inline-flex min-h-14 items-center justify-center gap-2 rounded-xl bg-white px-5 text-lg font-semibold text-brand-800 shadow-sm hover:bg-brand-50"
        >
          <CameraIcon className="size-6" />
          {t('citizenHome.report')}
        </Link>
      </section>

      <section aria-labelledby="recent-title" className="flex flex-col gap-3">
        <h2 id="recent-title" className="text-lg font-bold text-slate-900">
          {t('citizenHome.recentTitle')}
        </h2>
        {recent.isPending && <PageSkeleton rows={2} />}
        {recent.isError && <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />}
        {recent.isSuccess && recent.data.items.length === 0 && <EmptyState message={t('citizenHome.recentEmpty')} />}
        {recent.isSuccess && recent.data.items.length > 0 && (
          <>
            <ul className="flex flex-col gap-3">
              {recent.data.items.map((item) => (
                <li key={item.complaintId}>
                  <ComplaintCard complaint={item} />
                </li>
              ))}
            </ul>
            <Link to="/citizen/complaints" className={`${linkClass} self-start`}>
              {t('citizenHome.seeAll')}
            </Link>
          </>
        )}
      </section>

      <Link
        to="/citizen/profile"
        data-testid="home-profile"
        className="flex min-h-12 items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 font-medium text-slate-800 hover:bg-slate-50"
      >
        <UserCheckIcon className="size-5 text-brand-700" />
        {t('citizenHome.profile')}
      </Link>
    </div>
  );
}
