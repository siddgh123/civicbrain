import { useTranslation } from 'react-i18next';
import { EmptyState } from './EmptyState';

/** Screen shell for routes whose content comes in a later prompt (the title is already translated). */
export function PlaceholderPage({ title }: { title: string }) {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      <EmptyState message={t('common.notReady')} />
    </section>
  );
}
