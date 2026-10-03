import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { Link, Navigate, useNavigate } from 'react-router';
import { z } from 'zod';
import { authApi } from '../../api/auth';
import { PRIVACY_NOTICE_QUERY_KEY, publicApi } from '../../api/publicApi';
import { homePathForRole } from '../../auth/authContext';
import { useAuth } from '../../auth/useAuth';
import {
  CheckboxField,
  FormAlert,
  linkClass,
  PasswordField,
  primaryButtonClass,
  TextField,
} from '../../components/form/fields';
import {
  applyServerFieldErrors,
  EMAIL_PATTERN,
  hasControlChars,
  MOBILE_PATTERN,
  passwordLength,
} from '../../components/form/validation';
import { errorMessage } from '../../lib/errorMessage';
import { AuthCard } from './AuthCard';
import { PasswordStrength } from './PasswordStrength';
import { PrivacyNoticeBox } from './PrivacyNoticeBox';
import { verifyEmailPath, type VerifyEmailState } from './verifyEmailPath';

// Mirrors the backend RegisterRequest + password policy (docs/04 §1, docs/07 §1).
const registerSchema = z.object({
  fullName: z
    .string()
    .trim()
    .min(1, 'required')
    .max(150, 'tooLong')
    .refine((v) => !hasControlChars(v), 'controlChars'),
  email: z.string().trim().min(1, 'required').max(255, 'tooLong').regex(EMAIL_PATTERN, 'email'),
  phone: z
    .string()
    .transform((v) => v.replace(/[\s-]/g, ''))
    .pipe(z.string().min(1, 'required').regex(MOBILE_PATTERN, 'phone')),
  password: z
    .string()
    .min(1, 'required')
    .refine((v) => passwordLength(v) >= 12 && passwordLength(v) <= 128, 'passwordLength'),
  acceptPrivacy: z.boolean().refine((v) => v, 'acceptPrivacy'),
  whatsapp: z.boolean(),
  publicPhoto: z.boolean(),
  aiTraining: z.boolean(),
});
type RegisterInput = z.input<typeof registerSchema>;
type RegisterValues = z.output<typeof registerSchema>;

const FIELDS = ['fullName', 'email', 'phone', 'password'] as const;

/** docs/05_UI_SPEC.md §3 Register → OTP screen. Consents are separate and optional (07 §7). */
export function RegisterPage() {
  const { t } = useTranslation();
  const { status, user } = useAuth();
  const navigate = useNavigate();
  const notice = useQuery({ queryKey: PRIVACY_NOTICE_QUERY_KEY, queryFn: publicApi.privacyNotice });
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting },
  } = useForm<RegisterInput, unknown, RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: '',
      email: '',
      phone: '',
      password: '',
      acceptPrivacy: false,
      whatsapp: false,
      publicPhoto: false,
      aiTraining: false,
    },
  });
  const password = useWatch({ control, name: 'password' });

  if (status === 'signedIn' && user !== null) return <Navigate to={homePathForRole(user.role)} replace />;

  const onSubmit = handleSubmit(async (values) => {
    if (notice.data === undefined) return;
    setFormError(null);
    try {
      const otp = await authApi.register({
        fullName: values.fullName,
        email: values.email,
        phone: `+91${values.phone}`,
        password: values.password,
        privacyNoticeVersion: notice.data.version,
        consents: { whatsapp: values.whatsapp, publicPhoto: values.publicPhoto, aiTraining: values.aiTraining },
      });
      const state: VerifyEmailState = { email: values.email };
      void navigate(verifyEmailPath(otp.otpId, null), { state });
    } catch (error) {
      if (!applyServerFieldErrors(error, setError, FIELDS)) setFormError(errorMessage(t, error));
    }
  });

  return (
    <AuthCard title={t('pages.register')} intro={t('auth.registerIntro')}>
      <form noValidate onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-5">
        <TextField
          label={t('auth.fullName')}
          autoComplete="name"
          data-testid="register-name"
          error={errors.fullName?.message}
          {...register('fullName')}
        />
        <TextField
          label={t('auth.email')}
          type="email"
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          data-testid="register-email"
          error={errors.email?.message}
          {...register('email')}
        />
        <TextField
          label={t('auth.phone')}
          prefix={t('auth.phonePrefix')}
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          maxLength={12}
          hint={t('auth.phoneHint')}
          data-testid="register-phone"
          error={errors.phone?.message}
          {...register('phone')}
        />
        <PasswordField
          label={t('auth.password')}
          autoComplete="new-password"
          hint={t('auth.passwordHint')}
          extra={<PasswordStrength password={password} />}
          data-testid="register-password"
          error={errors.password?.message}
          {...register('password')}
        />

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1.5 font-semibold text-slate-900">{t('auth.privacyTitle')}</legend>
          <PrivacyNoticeBox query={notice} />
          <CheckboxField
            label={t('auth.acceptPrivacy')}
            data-testid="register-accept-privacy"
            error={errors.acceptPrivacy?.message}
            {...register('acceptPrivacy')}
          />
        </fieldset>

        <fieldset className="flex flex-col gap-1">
          <legend className="mb-1 font-semibold text-slate-900">{t('auth.optionalTitle')}</legend>
          <CheckboxField label={t('auth.consentWhatsapp')} data-testid="register-whatsapp" {...register('whatsapp')} />
          <CheckboxField
            label={t('auth.consentPublicPhoto')}
            data-testid="register-public-photo"
            {...register('publicPhoto')}
          />
          <CheckboxField
            label={t('auth.consentAiTraining')}
            data-testid="register-ai-training"
            {...register('aiTraining')}
          />
        </fieldset>

        {formError && <FormAlert>{formError}</FormAlert>}
        <button
          type="submit"
          disabled={isSubmitting || notice.data === undefined}
          data-testid="register-submit"
          className={primaryButtonClass}
        >
          {isSubmitting ? t('common.sending') : t('auth.submitRegister')}
        </button>
      </form>
      <p className="text-slate-700">
        {t('auth.haveAccount')}{' '}
        <Link to="/login" className={linkClass}>
          {t('common.login')}
        </Link>
      </p>
    </AuthCard>
  );
}
