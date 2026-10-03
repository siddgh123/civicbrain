import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { ME_QUERY_KEY, meApi, type ConsentType, type Me } from '../../api/me';
import { ErrorState } from '../../components/ErrorState';
import { CheckboxField, linkClass } from '../../components/form/fields';
import { PageSkeleton } from '../../components/PageSkeleton';
import { useToast } from '../../components/toast/useToast';
import { errorMessage } from '../../lib/errorMessage';

type Change =
  | { kind: 'optIn'; field: 'emailOptIn' | 'whatsappOptIn'; value: boolean }
  | { kind: 'consent'; type: ConsentType; value: boolean };

function granted(me: Me, type: ConsentType): boolean {
  return me.consents.find((c) => c.type === type)?.granted ?? false;
}

/**
 * Minimal profile (P07): account details, notification opt-ins (PUT /me) and photo consents (POST /me/consents) -
 * withdrawing is as easy as giving (docs/07_SECURITY.md §7). Language, data export and deletion come later.
 */
export function ProfilePage() {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const me = useQuery({ queryKey: ME_QUERY_KEY, queryFn: () => meApi.get() });
  const save = useMutation({
    mutationFn: (change: Change) => {
      if (change.kind === 'consent') return meApi.consent(change.type, change.value);
      const current = me.data;
      if (current === undefined) throw new Error('profile not loaded');
      return meApi.update({
        fullName: current.fullName,
        preferredLanguage: current.preferredLanguage,
        emailOptIn: change.field === 'emailOptIn' ? change.value : current.emailOptIn,
        whatsappOptIn: change.field === 'whatsappOptIn' ? change.value : current.whatsappOptIn,
      });
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(ME_QUERY_KEY, updated);
      toast.show({ message: t('profile.saved'), tone: 'success' });
    },
    onError: (error) => toast.show({ message: errorMessage(t, error), tone: 'error' }),
  });

  return (
    <section className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold text-slate-900">{t('pages.profile')}</h1>
        <p className="text-slate-700">{t('profile.intro')}</p>
      </div>
      {me.isPending && <PageSkeleton rows={3} />}
      {me.isError && <ErrorState error={me.error} onRetry={() => void me.refetch()} />}
      {me.data && (
        <>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="mb-3 font-semibold text-slate-900">{t('profile.account')}</h2>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-slate-800">
              <dt className="text-slate-600">{t('profile.name')}</dt>
              <dd className="break-words">{me.data.fullName}</dd>
              <dt className="text-slate-600">{t('profile.email')}</dt>
              <dd className="break-all">{me.data.email ?? '—'}</dd>
              <dt className="text-slate-600">{t('profile.phone')}</dt>
              <dd>{me.data.phoneMasked ?? '—'}</dd>
            </dl>
          </div>

          <fieldset disabled={save.isPending} className="rounded-xl border border-slate-200 bg-white p-4">
            <legend className="px-1 font-semibold text-slate-900">{t('profile.notifications')}</legend>
            <CheckboxField
              name="emailOptIn"
              label={t('profile.emailOptIn')}
              checked={me.data.emailOptIn}
              onChange={(e) => save.mutate({ kind: 'optIn', field: 'emailOptIn', value: e.target.checked })}
            />
            <CheckboxField
              name="whatsappOptIn"
              label={t('profile.whatsappOptIn')}
              checked={me.data.whatsappOptIn}
              onChange={(e) => save.mutate({ kind: 'optIn', field: 'whatsappOptIn', value: e.target.checked })}
            />
          </fieldset>

          <fieldset disabled={save.isPending} className="rounded-xl border border-slate-200 bg-white p-4">
            <legend className="px-1 font-semibold text-slate-900">{t('profile.consents')}</legend>
            <CheckboxField
              name="publicPhoto"
              label={t('profile.publicPhoto')}
              checked={granted(me.data, 'PUBLIC_PHOTO')}
              onChange={(e) => save.mutate({ kind: 'consent', type: 'PUBLIC_PHOTO', value: e.target.checked })}
            />
            <CheckboxField
              name="aiTraining"
              label={t('profile.aiTraining')}
              checked={granted(me.data, 'AI_TRAINING')}
              onChange={(e) => save.mutate({ kind: 'consent', type: 'AI_TRAINING', value: e.target.checked })}
            />
            <p className="mt-2 text-sm text-slate-600">{t('profile.consentHint')}</p>
          </fieldset>

          <div className="flex flex-col gap-3 sm:flex-row sm:gap-6">
            <Link to="/change-password" className={`${linkClass} flex min-h-11 items-center`}>
              {t('profile.changePassword')}
            </Link>
            <Link to="/privacy" className={`${linkClass} flex min-h-11 items-center`}>
              {t('profile.privacyNotice')}
            </Link>
          </div>
        </>
      )}
    </section>
  );
}
