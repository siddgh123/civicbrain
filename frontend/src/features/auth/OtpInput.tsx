import { useRef, type ClipboardEvent, type KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';

const LENGTH = 6;

interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  invalid?: boolean;
  describedBy?: string;
  disabled?: boolean;
}

/**
 * Six one-digit boxes (05 §3): typing moves to the next box, Backspace on an empty box goes back, and pasting a
 * code (or the phone's one-time-code autofill into the first box) fills all boxes at once.
 */
export function OtpInput({ value, onChange, invalid = false, describedBy, disabled = false }: OtpInputProps) {
  const { t } = useTranslation();
  const boxes = useRef<(HTMLInputElement | null)[]>([]);
  // `value` keeps a space for an empty box, so the other digits never shift position.
  const digits = Array.from({ length: LENGTH }, (_, i) => (value[i] ?? ' ').trim());
  const emit = (next: string[]) => onChange(next.map((d) => (d === '' ? ' ' : d)).join('').trimEnd());

  const focusBox = (index: number) => boxes.current[Math.max(0, Math.min(LENGTH - 1, index))]?.focus();

  /** Writes `typed` digits starting at box `start` and focuses the box after the last one written. */
  const fill = (start: number, typed: string) => {
    const incoming = typed.replace(/\D/g, '');
    if (incoming === '') return;
    const next = [...digits];
    let index = start;
    for (const digit of incoming) {
      if (index >= LENGTH) break;
      next[index] = digit;
      index += 1;
    }
    emit(next);
    focusBox(index);
  };

  const onPaste = (index: number) => (event: ClipboardEvent<HTMLInputElement>) => {
    event.preventDefault();
    const text = event.clipboardData.getData('text/plain') || event.clipboardData.getData('text');
    const pasted = text.replace(/\D/g, '');
    // A whole code always starts in the first box, wherever it was pasted.
    fill(pasted.length >= LENGTH ? 0 : index, pasted);
  };

  const onKeyDown = (index: number) => (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && digits[index] === '' && index > 0) {
      event.preventDefault();
      const next = [...digits];
      next[index - 1] = '';
      emit(next);
      focusBox(index - 1);
    } else if (event.key === 'ArrowLeft') {
      focusBox(index - 1);
    } else if (event.key === 'ArrowRight') {
      focusBox(index + 1);
    }
  };

  return (
    <div className="flex justify-between gap-2" role="group" aria-label={t('auth.otpLabel')} aria-describedby={describedBy}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(element) => {
            boxes.current[index] = element;
          }}
          value={digit}
          disabled={disabled}
          inputMode="numeric"
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          maxLength={index === 0 ? LENGTH : 1}
          aria-label={t('auth.otpDigit', { n: index + 1 })}
          aria-invalid={invalid || undefined}
          data-testid={`otp-digit-${index + 1}`}
          onPaste={onPaste(index)}
          onKeyDown={onKeyDown(index)}
          onFocus={(event) => event.target.select()}
          onChange={(event) => {
            const typed = event.target.value.replace(/\D/g, '');
            if (typed === '') {
              const next = [...digits];
              next[index] = '';
              emit(next);
              return;
            }
            // Autofill or a fast typist may put several digits into one box.
            fill(index, typed.length > 1 && digit !== '' ? typed.replace(digit, '') : typed);
          }}
          className={`h-14 w-full min-w-0 rounded-lg border bg-white text-center text-2xl font-semibold text-slate-900 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/30 ${
            invalid ? 'border-status-danger-fg' : 'border-slate-300'
          }`}
        />
      ))}
    </div>
  );
}
