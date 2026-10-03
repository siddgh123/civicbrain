import { use } from 'react';
import { ToastContext, type ToastContextValue } from './toastContext';

export function useToast(): ToastContextValue {
  const value = use(ToastContext);
  if (value === null) throw new Error('useToast must be used inside <ToastProvider>');
  return value;
}
