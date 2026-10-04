import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import type { SubmitResponse } from '../../../api/citizenComplaints';
import { primaryButtonClass, secondaryButtonClass } from '../../../components/form/fields';
import { BellIcon, CheckIcon } from '../../../components/icons/icons';

/** Step 5 (docs/05_UI_SPEC.md §4 step 4): the CB number, the ward from the server and where updates will come. */
export function SuccessStep({ result }: { result: SubmitResponse }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-5 rounded-2xl border border-status-success-border bg-white px-5 py-8 text-center">
      <span className="grid size-14 place-items-center rounded-full bg-status-success-bg text-status-success-fg">
        <CheckIcon className="size-8" />
      </span>
      <h2 role="status" className="text-xl font-bold text-slate-900">
        {t('wizard.successTitle')}
      </h2>
      <div className="flex flex-col gap-1">
        <p className="text-sm text-slate-600">{t('wizard.successRef')}</p>
        <p data-testid="success-ref" className="text-3xl font-bold tracking-wide text-brand-800 tabular-nums">
          {result.publicRef}
        </p>
        {result.wardNumber !== null && (
          <p className="font-medium text-slate-700">{t('wizard.successWard', { ward: result.wardNumber })}</p>
        )}
      </div>
      <p className="flex items-start gap-2 text-left text-slate-700">
        <BellIcon className="mt-0.5 size-5 shrink-0 text-brand-700" />
        {t('wizard.successUpdates')}
      </p>
      <div className="flex w-full flex-col gap-3">
        <Link to={`/citizen/complaints/${result.complaintId}`} data-testid="success-view" className={primaryButtonClass}>
          {t('wizard.viewComplaint')}
        </Link>
        <Link to="/citizen" className={`${secondaryButtonClass} w-full`}>
          {t('wizard.backHome')}
        </Link>
      </div>
    </div>
  );
}
