import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { primaryButtonClass } from '../../../components/form/fields';
import { SearchIcon } from '../../../components/icons/icons';

/** Friendly 404 for a complaint that is not the citizen's or does not exist (the API does not say which). */
export function ComplaintNotFound({ title, text }: { title: string; text: string }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center">
      <span className="grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-500">
        <SearchIcon className="size-8" />
      </span>
      <h1 className="text-xl font-bold text-slate-900">{title}</h1>
      <p className="text-slate-700">{text}</p>
      <Link to="/citizen/complaints" className={`${primaryButtonClass} max-w-xs`}>
        {t('complaintDetail.toList')}
      </Link>
    </div>
  );
}
