import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router';
import { z } from 'zod';
import { emailNotVerifiedSchema } from '../../api/auth';
import { pathAfterLogin } from '../../auth/authContext';
import { useAuth } from '../../auth/useAuth';
import { FormAlert, linkClass, PasswordField, primaryButtonClass, TextField } from '../../components/form/fields';
import { isValidIdentifier, passwordLength } from '../../components/form/validation';
import { ApiError } from '../../lib/api';
import { errorMessage } from '../../lib/errorMessage';
import { AuthCard } from './AuthCard';
import { verifyEmailPath, type VerifyEmailState } from './verifyEmailPath';

const loginSchema = z.object({
  identifier: z
    .string()
    .trim()
    .min(1, 'required')
    .max(255, 'tooLong')
    .superRefine((value, ctx) => {
      if (!isValidIdentifier(value)) ctx.addIssue({ code: 'custom', message: value.includes('@') ? 'email' : 'identifier' });
    }),
  password: z
    .string()
    .min(1, 'required')
    .refine((v) => passwordLength(v) >= 12 && passwordLength(v) <= 128, 'passwordLength'),
});
type LoginForm = z.input<typeof loginSchema>;

interface LoginLocationState {
  verified?: boolean;
  identifier?: string;
}

function readState(state: unknown): LoginLocationState {
  const parsed = z.object({ verified: z.boolean().optional(), identifier: z.string().optional() }).safeParse(state);
  return parsed.success ? parsed.data : {};
}

/** docs/05_UI_SPEC.md §3 Login: identifier (e-mail or +91 mobile) + password; unverified e-mail → OTP screen. */
export function LoginPage() {
  const { t } = useTranslation();
  const { status, user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const returnTo = params.get('returnTo');
  const notice = readState(location.state);
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: notice.identifier ?? '', password: '' },
  });

  if (status === 'signedIn' && user !== null) return <Navigate to={pathAfterLogin(user, returnTo)} replace />;

  const onSubmit = handleSubmit(async ({ identifier, password }) => {
    setFormError(null);
    try {
      const outcome = await login(identifier.trim(), password);
      if (outcome.kind === 'mfa') setFormError(t('auth.mfaNotAvailable'));
      // signed in: this page re-renders and redirects (above)
    } catch (error) {
      if (error instanceof ApiError && error.code === 'EMAIL_NOT_VERIFIED') {
        const otp = emailNotVerifiedSchema.safeParse(error.extensions);
        if (otp.success) {
          const state: VerifyEmailState = { email: identifier.includes('@') ? identifier.trim() : undefined };
          void navigate(verifyEmailPath(otp.data.otpId, returnTo), { state });
          return;
        }
      }
      setFormError(errorMessage(t, error));
    }
  });

  return (
    <AuthCard title={t('pages.login')} intro={t('auth.loginIntro')}>
      {notice.verified && <FormAlert tone="success">{t('auth.verifiedNotice')}</FormAlert>}
      <form noValidate onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-5">
        <TextField
          label={t('auth.identifier')}
          type="text"
          autoComplete="username"
          inputMode="email"
          autoCapitalize="none"
          spellCheck={false}
          data-testid="login-identifier"
          error={errors.identifier?.message}
          {...register('identifier')}
        />
        <PasswordField
          label={t('auth.password')}
          autoComplete="current-password"
          data-testid="login-password"
          error={errors.password?.message}
          {...register('password')}
        />
        {formError && <FormAlert>{formError}</FormAlert>}
        <button type="submit" disabled={isSubmitting} data-testid="login-submit" className={primaryButtonClass}>
          {isSubmitting ? t('common.sending') : t('auth.submitLogin')}
        </button>
      </form>
      <p className="text-slate-700">
        {t('auth.noAccount')}{' '}
        <Link to="/register" className={linkClass}>
          {t('auth.createAccount')}
        </Link>
      </p>
    </AuthCard>
  );
}
