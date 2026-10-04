import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { CATEGORIES_QUERY_KEY, publicApi, type Category } from '../../../api/publicApi';
import { EmptyState } from '../../../components/EmptyState';
import { ErrorState } from '../../../components/ErrorState';
import { FormAlert } from '../../../components/form/fields';
import { CategoryIcon } from './CategoryIcon';

interface CategoryStepProps {
  selectedId: number | null;
  onSelect: (category: Category) => void;
  /** Why the citizen is back here (the server refused the category). */
  notice?: string | null;
}

/**
 * Step 1: large tiles for the citizen-selectable categories only (docs/05_UI_SPEC.md §4 step 1; V6 MVP scope: 5 of
 * the 8). With an odd number of tiles the last one ("Other") spans the whole row.
 */
export function CategoryStep({ selectedId, onSelect, notice = null }: CategoryStepProps) {
  const { t } = useTranslation();
  const categories = useQuery({ queryKey: CATEGORIES_QUERY_KEY, queryFn: ({ signal }) => publicApi.categories(signal) });

  if (categories.isPending) {
    return (
      <div role="status" aria-busy="true" aria-label={t('common.loading')} className="grid grid-cols-2 gap-3">
        {Array.from({ length: 8 }, (_, i) => (
          <div key={i} className="h-28 rounded-2xl bg-slate-200 motion-safe:animate-pulse" />
        ))}
      </div>
    );
  }
  if (categories.isError) return <ErrorState error={categories.error} onRetry={() => void categories.refetch()} />;

  const selectable = categories.data.filter((c) => c.citizenSelectable);
  if (selectable.length === 0) return <EmptyState message={t('wizard.categoriesEmpty')} />;
  return (
    <div className="flex flex-col gap-3">
      {notice !== null && <FormAlert>{notice}</FormAlert>}
      <p className="text-slate-700">{t('wizard.categoryIntro')}</p>
      <ul className="grid grid-cols-2 gap-3">
        {selectable.map((category, index) => {
          const selected = category.id === selectedId;
          const fullRow = selectable.length % 2 === 1 && index === selectable.length - 1;
          return (
            <li key={category.id} className={fullRow ? 'col-span-2' : undefined}>
              <button
                type="button"
                onClick={() => onSelect(category)}
                aria-pressed={selected}
                data-testid={`category-tile-${category.id}`}
                className={`flex min-h-28 w-full flex-col items-center justify-center gap-2 rounded-2xl border-2 px-3 py-4 text-center font-semibold leading-snug shadow-sm ${
                  selected
                    ? 'border-brand-700 bg-brand-50 text-brand-900'
                    : 'border-slate-200 bg-white text-slate-900 hover:border-brand-600 hover:bg-brand-50'
                }`}
              >
                <CategoryIcon name={category.name} className="size-9 text-brand-700" />
                {category.name}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
