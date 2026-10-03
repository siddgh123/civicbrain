import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckIcon, AlertIcon, BellIcon, XIcon } from '../icons/icons';
import { ToastContext, type ToastInput, type ToastTone } from './toastContext';

const AUTO_HIDE_MS = 6000;

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

const TONE_CLASSES: Record<ToastTone, string> = {
  info: 'border-status-info-border bg-status-info-bg text-status-info-fg',
  success: 'border-status-success-border bg-status-success-bg text-status-success-fg',
  error: 'border-status-danger-border bg-status-danger-bg text-status-danger-fg',
};

const TONE_ICON = { info: BellIcon, success: CheckIcon, error: AlertIcon } as const;

/** Toasts for mutation results; the region is `aria-live` so screen readers announce them (05 §2). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer !== undefined) clearTimeout(timer);
    timers.current.delete(id);
    setToasts((list) => list.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    ({ message, tone = 'info' }: ToastInput) => {
      const id = nextId.current++;
      setToasts((list) => [...list, { id, message, tone }]);
      timers.current.set(
        id,
        setTimeout(() => dismiss(id), AUTO_HIDE_MS),
      );
    },
    [dismiss],
  );

  useEffect(() => {
    const pending = timers.current;
    return () => {
      for (const timer of pending.values()) clearTimeout(timer);
      pending.clear();
    };
  }, []);

  const value = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext value={value}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 md:bottom-6 md:items-end"
      >
        {toasts.map((toast) => {
          const Icon = TONE_ICON[toast.tone];
          return (
            <div
              key={toast.id}
              data-testid="toast"
              className={`pointer-events-auto flex w-full max-w-sm items-start gap-2 rounded-xl border px-4 py-3 shadow-lg ${TONE_CLASSES[toast.tone]}`}
            >
              <Icon className="mt-0.5 size-5 shrink-0" />
              <p className="flex-1 text-sm font-medium">{toast.message}</p>
              <button
                type="button"
                onClick={() => dismiss(toast.id)}
                aria-label={t('common.dismiss')}
                className="-m-2 grid size-11 shrink-0 place-items-center rounded-lg hover:bg-black/5"
              >
                <XIcon className="size-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext>
  );
}
