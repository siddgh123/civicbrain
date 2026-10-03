import { useSyncExternalStore } from 'react';
import { useTranslation } from 'react-i18next';
import { WifiOffIcon } from './icons/icons';

function subscribe(onChange: () => void): () => void {
  window.addEventListener('online', onChange);
  window.addEventListener('offline', onChange);
  return () => {
    window.removeEventListener('online', onChange);
    window.removeEventListener('offline', onChange);
  };
}

/** Banner while `navigator.onLine` is false (docs/05_UI_SPEC.md §2). */
export function OfflineBanner() {
  const { t } = useTranslation();
  const online = useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true,
  );
  if (online) return null;
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 bg-status-warning-bg px-4 py-2 text-sm font-medium text-status-warning-fg"
    >
      <WifiOffIcon className="size-4 shrink-0" />
      {t('common.offline')}
    </div>
  );
}
