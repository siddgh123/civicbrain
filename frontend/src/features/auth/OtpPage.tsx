import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useId, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router';
import { z } from 'zod';
import { authApi } from '../../api/auth';
import { FieldError, FormAlert, linkClass, primaryButtonClass, secondaryButtonClass } from '../../components/form/fields';
import { ApiError } from '../../lib/api';
import { errorMessage } from '../../lib/errorMessage';
import { AuthCard } from './AuthCard';
import { OtpInput } from './OtpInput';

const RESEND_SECONDS = 60;

const otpSchema = z.object({ code: z.string().regex(/^\d{6}$/, 'otp') });
type OtpForm = z.input<typeof otpSchema>;

function readOtpId(raw: string | null): number | null {
  if (raw === null || !/^\d{1,18}$/.test(raw)) return null;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

function readEmail(state: unknown): string | undefined {
  const parsed = z.object({ email: z.string().optional() }).safeParse(state);
  return parsed.success ? parsed.data.email : undefined;
}

/** docs/05_UI_SPEC.md §3: 6 boxes (paste-friendly), resend after 60 s (04 §11: 1 per 60 s per destination). */
export function OtpPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const otpId = readOtpId(params.get('otpId'));
  const returnTo = params.get('returnTo');
  const email = readEmail(useLocation().state);
  const navigate = useNavigate();
  const errorId = useId();
  const [formError, setFormError] = useState<string | null>(null);
  const [resent, setResent] = useState(false);
  const [resending, setResending] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(RESEND_SECONDS);
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OtpForm>({ resolver: zodResolver(otpSchema), defaultValues: { code: '' } });

  useEffect(() => {
    if (secondsLeft <= 0) return undefined;
    const timer = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  if (otpId === null) {
    return (
      <AuthCard title={t('pages.verifyEmail')}>
        <FormAlert>{t('auth.otpMissing')}</FormAlert>
        <p className="flex flex-wrap gap-4">
          <Link to="/register" className={linkClass}>
            {t('auth.createAccount')}
          </Link>
          <Link to="/login" className={linkClass}>
            {t('common.login')}
          </Link>
        </p>
      </AuthCard>
    );
  }

  const onSubmit = handleSubmit(async ({ code }) => {
    setFormError(null);
    setResent(false);
    try {
      await authApi.verifyOtp(otpId, code);
      const login = returnTo === null ? '/login' : `/login?${new URLSearchParams({ returnTo }).toString()}`;
      void navigate(login, { replace: true, state: { verified: true, identifier: email } });
    } catch (error) {
      setFormError(errorMessage(t, error));
    }
  });

  const onResend = async () => {
    setFormError(null);
    setResent(false);
    setResending(true);
    try {
      await authApi.resendOtp(otpId);
      setResent(true);
      setSecondsLeft(RESEND_SECONDS);
    } catch (error) {
      if (error instanceof ApiError && error.retryAfterSeconds !== null) setSecondsLeft(error.retryAfterSeconds);
      setFormError(errorMessage(t, error));
    } finally {
      setResending(false);
    }
  };

  return (
    <AuthCard
      title={t('pages.verifyEmail')}
      intro={email ? t('auth.otpIntroEmail', { email }) : t('auth.otpIntro')}
    >
      <form noValidate onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-5">
        <Controller
          control={control}
          name="code"
          render={({ field }) => (
            <OtpInput
              value={field.value}
              onChange={field.onChange}
              invalid={errors.code !== undefined}
              describedBy={errors.code ? errorId : undefined}
            />
          )}
        />
        <FieldError id={errorId} message={errors.code?.message} />
        {formError && <FormAlert>{formError}</FormAlert>}
        {resent && <FormAlert tone="success">{t('auth.otpResent')}</FormAlert>}
        <button type="submit" disabled={isSubmitting} data-testid="otp-submit" className={primaryButtonClass}>
          {isSubmitting ? t('common.sending') : t('auth.otpSubmit')}
        </button>
      </form>
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => void onResend()}
          disabled={secondsLeft > 0 || resending}
          data-testid="otp-resend"
          className={secondaryButtonClass}
        >
          {secondsLeft > 0 ? t('auth.otpResendIn', { seconds: secondsLeft }) : t('auth.otpResend')}
        </button>
        <p className="text-sm text-slate-600">{t('auth.otpNoMail')}</p>
      </div>
    </AuthCard>
  );
}
