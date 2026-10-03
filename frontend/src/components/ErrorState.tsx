import { useTranslation } from 'react-i18next';
import { ApiError } from '../lib/api';
import { errorMessage } from '../lib/errorMessage';
import { AlertIcon } from './icons/icons';

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
}

/** Query error: message by code + "Try again" + requestId in small text (docs/12_ERROR_HANDLING.md §6). */
export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const { t } = useTranslation();
  const requestId = error instanceof ApiError ? error.requestId : null;
  // INTERNAL_ERROR already says "Reference: <requestId>" in its message.
  const showReference = requestId !== null && !(error instanceof ApiError && error.code === 'INTERNAL_ERROR');
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-status-danger-border bg-status-danger-bg px-6 py-8 text-center">
      <AlertIcon className="size-8 text-status-danger-fg" />
      <p role="alert" className="font-medium text-status-danger-fg">
        {errorMessage(t, error)}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="min-h-11 rounded-lg bg-white px-4 font-medium text-slate-900 ring-1 ring-slate-300 hover:bg-slate-50"
        >
          {t('common.tryAgain')}
        </button>
      )}
      {showReference && <p className="text-xs text-slate-600">{t('common.reference', { requestId })}</p>}
    </div>
  );
}
