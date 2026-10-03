import { useId, useState, type InputHTMLAttributes, type ReactNode, type Ref } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertIcon } from '../icons/icons';
import { validationText } from './validation';

// Labelled inputs for react-hook-form (`{...register('x')}` passes name/onChange/onBlur/ref). Every input has a label,
// a hint and its error are linked with aria-describedby, touch targets are ≥ 44 px (docs/05_UI_SPEC.md §2).

const inputClass =
  'min-h-12 w-full rounded-lg border bg-white px-3 text-base text-slate-900 placeholder:text-slate-400 ' +
  'focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/30 disabled:bg-slate-100';

function borderClass(error: string | undefined): string {
  return error ? 'border-status-danger-fg' : 'border-slate-300';
}

export function FieldError({ id, message }: { id: string; message: string | undefined }) {
  const { t } = useTranslation();
  if (!message) return null;
  return (
    <p id={id} className="flex items-start gap-1.5 text-sm font-medium text-status-danger-fg">
      <AlertIcon className="mt-0.5 size-4 shrink-0" />
      {validationText(t, message)}
    </p>
  );
}

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'prefix'> {
  label: string;
  name: string;
  error?: string;
  hint?: string;
  /** Fixed text before the input, e.g. "+91". */
  prefix?: string;
  ref?: Ref<HTMLInputElement>;
}

export function TextField({ label, error, hint, prefix, ref, className, ...input }: TextFieldProps) {
  const id = useId();
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(' ');
  return (
    <div className={`flex flex-col gap-1.5 ${className ?? ''}`}>
      <label htmlFor={id} className="font-medium text-slate-900">
        {label}
      </label>
      <div className="flex">
        {prefix && (
          <span className="flex min-h-12 items-center rounded-l-lg border border-r-0 border-slate-300 bg-slate-100 px-3 text-base font-medium text-slate-700">
            {prefix}
          </span>
        )}
        <input
          id={id}
          ref={ref}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          className={`${inputClass} ${borderClass(error)} ${prefix ? 'rounded-l-none' : ''}`}
          {...input}
        />
      </div>
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-slate-600">
          {hint}
        </p>
      )}
      <FieldError id={`${id}-error`} message={error} />
    </div>
  );
}

interface PasswordFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  name: string;
  error?: string;
  hint?: string;
  /** Live hint under the input (e.g. the strength meter). */
  extra?: ReactNode;
  ref?: Ref<HTMLInputElement>;
}

/** Password input with a show/hide toggle (05 §3 Register). */
export function PasswordField({ label, error, hint, extra, ref, ...input }: PasswordFieldProps) {
  const { t } = useTranslation();
  const id = useId();
  const [visible, setVisible] = useState(false);
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(' ');
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="font-medium text-slate-900">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          ref={ref}
          type={visible ? 'text' : 'password'}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          className={`${inputClass} ${borderClass(error)} pr-20`}
          {...input}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-pressed={visible}
          aria-controls={id}
          className="absolute inset-y-0 right-0 min-w-11 rounded-r-lg px-3 text-sm font-semibold text-brand-800 hover:bg-brand-50"
        >
          {visible ? t('auth.hidePassword') : t('auth.showPassword')}
        </button>
      </div>
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-slate-600">
          {hint}
        </p>
      )}
      {extra}
      <FieldError id={`${id}-error`} message={error} />
    </div>
  );
}

interface CheckboxFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  name: string;
  error?: string;
  ref?: Ref<HTMLInputElement>;
}

export function CheckboxField({ label, error, ref, ...input }: CheckboxFieldProps) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="flex min-h-11 cursor-pointer items-start gap-3 py-1.5 text-slate-800">
        <input
          id={id}
          ref={ref}
          type="checkbox"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          className="mt-0.5 size-5 shrink-0 cursor-pointer accent-brand-700"
          {...input}
        />
        <span>{label}</span>
      </label>
      <FieldError id={`${id}-error`} message={error} />
    </div>
  );
}

/** Form-level message (server error without a field, or a notice). */
export function FormAlert({ tone = 'error', children }: { tone?: 'error' | 'success' | 'info'; children: ReactNode }) {
  const classes = {
    error: 'border-status-danger-border bg-status-danger-bg text-status-danger-fg',
    success: 'border-status-success-border bg-status-success-bg text-status-success-fg',
    info: 'border-status-info-border bg-status-info-bg text-status-info-fg',
  }[tone];
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`rounded-lg border px-4 py-3 font-medium ${classes}`}>
      {children}
    </div>
  );
}

// py + text-center: a label that wraps on a 360 px screen keeps its padding and stays centred.
export const primaryButtonClass =
  'inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand-700 px-5 py-2.5 text-center text-base font-semibold leading-snug ' +
  'text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:bg-slate-400';

export const secondaryButtonClass =
  'inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-white px-5 py-2.5 text-center text-base font-semibold leading-snug ' +
  'text-brand-800 ring-1 ring-brand-700/40 hover:bg-brand-50 disabled:cursor-not-allowed disabled:text-slate-400 disabled:ring-slate-300';

export const linkClass = 'font-semibold text-brand-800 underline underline-offset-2 hover:text-brand-900';
