import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { z } from 'zod';
import { authApi } from '../../api/auth';
import { homePathForRole } from '../../auth/authContext';
import { useAuth } from '../../auth/useAuth';
import { FormAlert, PasswordField, primaryButtonClass } from '../../components/form/fields';
import { applyServerFieldErrors, passwordLength } from '../../components/form/validation';
import { useToast } from '../../components/toast/useToast';
import { errorMessage } from '../../lib/errorMessage';
import { AuthCard } from './AuthCard';
import { PasswordStrength } from './PasswordStrength';

const lengthOk = (v: string) => passwordLength(v) >= 12 && passwordLength(v) <= 128;

const changeSchema = z
  .object({
    currentPassword: z.string().min(1, 'required'),
    newPassword: z.string().min(1, 'required').refine(lengthOk, 'passwordLength'),
    confirmPassword: z.string().min(1, 'required'),
  })
  .refine((v) => v.newPassword === v.confirmPassword, { path: ['confirmPassword'], message: 'passwordMatch' });
type ChangeForm = z.input<typeof changeSchema>;

const FIELDS = ['currentPassword', 'newPassword'] as const;

/**
 * POST /auth/password/change (04 §1). Forced after a one-time password (`mustChangePassword`, 05 §3); the server
 * revokes the old access token, so the session is refreshed with the cookie before going on.
 */
export function ChangePasswordPage() {
  const { t } = useTranslation();
  const { user, refreshSession } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ChangeForm>({
    resolver: zodResolver(changeSchema),
    defaultValues: { currentPassword: '', newPassword: '', confirmPassword: '' },
  });
  const newPassword = useWatch({ control, name: 'newPassword' });
  const forced = user?.mustChangePassword === true;

  const onSubmit = handleSubmit(async ({ currentPassword, newPassword: chosen }) => {
    setFormError(null);
    try {
      await authApi.changePassword(currentPassword, chosen);
    } catch (error) {
      if (!applyServerFieldErrors(error, setError, FIELDS)) setFormError(errorMessage(t, error));
      return;
    }
    toast.show({ message: t('auth.passwordChanged'), tone: 'success' });
    if (await refreshSession()) {
      void navigate(user === null ? '/' : homePathForRole(user.role), { replace: true });
    } else {
      void navigate('/login', { replace: true });
    }
  });

  return (
    <AuthCard title={t('pages.changePassword')} intro={forced ? t('auth.changeIntroForced') : t('auth.changeIntro')}>
      <form noValidate onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-5">
        <PasswordField
          label={t('auth.currentPassword')}
          autoComplete="current-password"
          data-testid="change-current"
          error={errors.currentPassword?.message}
          {...register('currentPassword')}
        />
        <PasswordField
          label={t('auth.newPassword')}
          autoComplete="new-password"
          hint={t('auth.passwordHint')}
          extra={<PasswordStrength password={newPassword} />}
          data-testid="change-new"
          error={errors.newPassword?.message}
          {...register('newPassword')}
        />
        <PasswordField
          label={t('auth.confirmPassword')}
          autoComplete="new-password"
          data-testid="change-confirm"
          error={errors.confirmPassword?.message}
          {...register('confirmPassword')}
        />
        {formError && <FormAlert>{formError}</FormAlert>}
        <button type="submit" disabled={isSubmitting} data-testid="change-submit" className={primaryButtonClass}>
          {isSubmitting ? t('common.saving') : t('auth.submitChange')}
        </button>
      </form>
    </AuthCard>
  );
}
