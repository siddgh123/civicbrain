import { useTranslation } from 'react-i18next';

/** Loading placeholder for pages and lists (skeletons, not spinners - docs/05_UI_SPEC.md §2). */
export function PageSkeleton({ rows = 4 }: { rows?: number }) {
  const { t } = useTranslation();
  return (
    <div role="status" aria-busy="true" aria-label={t('common.loading')} className="flex flex-col gap-3">
      <div className="h-7 w-1/2 rounded-md bg-slate-200 motion-safe:animate-pulse" />
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-16 rounded-xl bg-slate-200 motion-safe:animate-pulse" />
      ))}
    </div>
  );
}
