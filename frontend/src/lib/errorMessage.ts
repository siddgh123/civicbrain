import type { TFunction } from 'i18next';
import en from '../i18n/en.json';
import { ApiError } from './api';

export type ErrorMessageCode = keyof typeof en.errors;

function isKnownCode(code: string): code is ErrorMessageCode {
  return Object.hasOwn(en.errors, code);
}

/** The user-facing text for any thrown value (docs/12_ERROR_HANDLING.md §2, §6). Never shows raw server text. */
export function errorMessage(t: TFunction, error: unknown): string {
  if (!(error instanceof ApiError) || !isKnownCode(error.code)) return t('errors.UNKNOWN');
  return t(`errors.${error.code}`, {
    seconds: error.retryAfterSeconds ?? 60,
    requestId: error.requestId ?? '—',
  });
}
