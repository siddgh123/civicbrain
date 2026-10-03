import type { TFunction } from 'i18next';
import type { FieldValues, Path, UseFormSetError } from 'react-hook-form';
import en from '../../i18n/en.json';
import { ApiError } from '../../lib/api';

/** zod messages and mapped server field errors are keys of `validation.*` in en.json. */
export type ValidationKey = keyof typeof en.validation;

function isValidationKey(value: string): value is ValidationKey {
  return Object.hasOwn(en.validation, value);
}

export function validationText(t: TFunction, message: string): string {
  return t(`validation.${isValidationKey(message) ? message : 'invalid'}`);
}

/** Server field-error codes (GlobalExceptionHandler, PasswordPolicy, DbErrorTranslator) → message key. */
function keyForServerCode(field: string, code: string): ValidationKey {
  switch (code) {
    case 'PASSWORD_POLICY':
      return 'passwordPolicy';
    case 'INCORRECT':
      return 'incorrect';
    case 'ALREADY_EXISTS':
      return 'alreadyExists';
    case 'NOT_BLANK':
    case 'NOT_NULL':
      return 'required';
    default:
      if (field === 'email') return 'email';
      if (field === 'phone') return 'phone';
      return 'invalid';
  }
}

/**
 * Puts the server's `fieldErrors` on the matching form fields (docs/05_UI_SPEC.md §2). `fieldMap` renames API
 * fields (e.g. `newPassword` → `password`). Returns false when nothing could be mapped (show a form-level message).
 */
export function applyServerFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
  fieldMap: Partial<Record<string, Path<T>>> = {},
): boolean {
  if (!(error instanceof ApiError)) return false;
  let applied = false;
  for (const item of error.fieldErrors) {
    const target = fieldMap[item.field] ?? fields.find((f) => f === item.field);
    if (target === undefined) continue;
    setError(target, { type: 'server', message: keyForServerCode(item.field, item.code) }, { shouldFocus: !applied });
    applied = true;
  }
  return applied;
}

/** Password length in code points, as the server counts it (07 §1: 12–128 characters). */
export function passwordLength(value: string): number {
  return [...value].length;
}

const CONTROL_CHARS = /\p{Cc}/u;

export function hasControlChars(value: string): boolean {
  return CONTROL_CHARS.test(value);
}

/** Same pattern as the backend RegisterRequest (`^[^@\s]+@[^@\s]+\.[^@\s]+$`). */
export const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** 10-digit Indian mobile number without +91 (backend: `^\+91[6-9][0-9]{9}$`). */
export const MOBILE_PATTERN = /^[6-9]\d{9}$/;

/** Login identifier: an e-mail, or a mobile number in a form the backend normalises (+91 / 91 / 0 prefix). */
export function isValidIdentifier(value: string): boolean {
  const s = value.trim();
  if (s.includes('@')) return EMAIL_PATTERN.test(s);
  return /^(\+?91|0)?[6-9]\d{9}$/.test(s.replace(/[\s()-]/g, ''));
}
