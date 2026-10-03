import { createContext } from 'react';

export type ToastTone = 'info' | 'success' | 'error';

export interface ToastInput {
  message: string;
  tone?: ToastTone;
}

export interface ToastContextValue {
  show: (toast: ToastInput) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);
