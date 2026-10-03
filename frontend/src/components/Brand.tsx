import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { MapPinIcon } from './icons/icons';

export function Brand({ to = '/' }: { to?: string }) {
  const { t } = useTranslation();
  return (
    <Link to={to} className="flex min-h-11 items-center gap-2 rounded-lg text-lg font-bold text-slate-900">
      <span className="grid size-8 place-items-center rounded-lg bg-brand-700 text-white">
        <MapPinIcon className="size-5" />
      </span>
      {t('app.name')}
    </Link>
  );
}
