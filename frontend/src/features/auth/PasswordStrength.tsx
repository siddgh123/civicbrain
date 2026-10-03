import { useTranslation } from 'react-i18next';
import { passwordLength } from '../../components/form/validation';

type Level = 'empty' | 'short' | 'long' | 'ok' | 'strong';

/** A hint, not a rule: 07 §1 allows any characters and has no composition rules, so only length counts. */
function strengthLevel(password: string): Level {
  const length = passwordLength(password);
  if (length === 0) return 'empty';
  if (length < 12) return 'short';
  if (length > 128) return 'long';
  return length >= 16 ? 'strong' : 'ok';
}

const BAR: Record<Level, { filled: number; color: string }> = {
  empty: { filled: 0, color: 'bg-slate-300' },
  short: { filled: 1, color: 'bg-status-danger-fg' },
  long: { filled: 1, color: 'bg-status-danger-fg' },
  ok: { filled: 2, color: 'bg-status-warning-fg' },
  strong: { filled: 3, color: 'bg-status-success-fg' },
};

export function PasswordStrength({ password }: { password: string }) {
  const { t } = useTranslation();
  const level = strengthLevel(password);
  if (level === 'empty') return null;
  const text = {
    short: t('auth.strengthShort', { count: passwordLength(password) }),
    long: t('auth.strengthLong'),
    ok: t('auth.strengthOk'),
    strong: t('auth.strengthStrong'),
  }[level];
  const { filled, color } = BAR[level];
  return (
    <div className="flex flex-col gap-1" data-testid="password-strength">
      <div className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span key={i} className={`h-1.5 flex-1 rounded-full ${i < filled ? color : 'bg-slate-200'}`} />
        ))}
      </div>
      <p aria-live="polite" className="text-sm text-slate-700">
        {text}
      </p>
    </div>
  );
}
