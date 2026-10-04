import { useInfiniteQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { CITIZEN_COMPLAINTS_KEY, citizenApi, OWN_PAGE_SIZE } from '../../../api/citizenComplaints';
import { EmptyState } from '../../../components/EmptyState';
import { ErrorState } from '../../../components/ErrorState';
import { primaryButtonClass, secondaryButtonClass } from '../../../components/form/fields';
import { CameraIcon, RotateIcon } from '../../../components/icons/icons';
import { PageSkeleton } from '../../../components/PageSkeleton';
import { isClosedForCitizen } from '../../../lib/complaintStatus';
import { ComplaintCard } from './ComplaintCard';
import { usePullToRefresh } from './usePullToRefresh';

type Filter = 'open' | 'closed';

/**
 * `/citizen/complaints` (docs/05_UI_SPEC.md §4.6, FR-13): the citizen's own complaints, newest first, with Open /
 * Closed chips, skeleton, empty state, Refresh button + pull-to-refresh. The API has a single-status filter only, so
 * the chips filter the loaded pages (100 per page; more load with "Show older complaints").
 */
export function ComplaintsListPage() {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<Filter>('open');
  const list = useInfiniteQuery({
    queryKey: [...CITIZEN_COMPLAINTS_KEY, 'all'],
    queryFn: ({ pageParam, signal }) => citizenApi.list(pageParam, OWN_PAGE_SIZE, signal),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.page + 1 < last.totalPages ? last.page + 1 : undefined),
  });
  const pullReady = usePullToRefresh(() => void list.refetch());

  const items = list.data?.pages.flatMap((page) => page.items) ?? [];
  const shown = items.filter((item) => isClosedForCitizen(item.status) === (filter === 'closed'));
  const reportLink = (
    <Link to="/citizen/new" className={`${primaryButtonClass} max-w-xs`}>
      <CameraIcon className="size-5" />
      {t('complaints.report')}
    </Link>
  );

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">{t('pages.citizenComplaints')}</h1>
        {list.isSuccess && (
          <button
            type="button"
            onClick={() => void list.refetch()}
            disabled={list.isFetching}
            data-testid="complaints-refresh"
            className={`${secondaryButtonClass} min-h-11 px-3 text-sm`}
          >
            <RotateIcon className={`size-4 ${list.isRefetching ? 'motion-safe:animate-spin' : ''}`} />
            {list.isRefetching ? t('complaints.refreshing') : t('complaints.refresh')}
          </button>
        )}
      </div>
      {pullReady && (
        <p role="status" className="text-center text-sm font-medium text-brand-800">
          {t('complaints.pullRelease')}
        </p>
      )}

      {list.isPending && <PageSkeleton rows={3} />}
      {list.isError && <ErrorState error={list.error} onRetry={() => void list.refetch()} />}
      {list.isSuccess && items.length === 0 && <EmptyState message={t('complaints.emptyAll')} action={reportLink} />}
      {list.isSuccess && items.length > 0 && (
        <>
          <div role="group" aria-label={t('complaints.filterLabel')} className="flex gap-2">
            {(['open', 'closed'] as const).map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
                data-testid={`filter-${value}`}
                className={`min-h-11 rounded-full border px-5 font-semibold ${
                  filter === value
                    ? 'border-brand-700 bg-brand-700 text-white'
                    : 'border-slate-300 bg-white text-slate-800 hover:bg-slate-50'
                }`}
              >
                {value === 'open' ? t('complaints.filterOpen') : t('complaints.filterClosed')}
              </button>
            ))}
          </div>
          {shown.length === 0 ? (
            <EmptyState
              message={filter === 'open' ? t('complaints.emptyOpen') : t('complaints.emptyClosed')}
              action={filter === 'open' ? reportLink : undefined}
            />
          ) : (
            <ul aria-label={t('pages.citizenComplaints')} className="flex flex-col gap-3">
              {shown.map((item) => (
                <li key={item.complaintId}>
                  <ComplaintCard complaint={item} />
                </li>
              ))}
            </ul>
          )}
          {list.hasNextPage && (
            <button
              type="button"
              onClick={() => void list.fetchNextPage()}
              disabled={list.isFetchingNextPage}
              className={secondaryButtonClass}
            >
              {list.isFetchingNextPage ? t('common.loading') : t('complaints.loadMore')}
            </button>
          )}
        </>
      )}
    </section>
  );
}
