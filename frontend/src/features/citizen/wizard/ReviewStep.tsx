import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import type { Category } from '../../../api/publicApi';
import { FormAlert, primaryButtonClass, secondaryButtonClass } from '../../../components/form/fields';
import { PinMap } from '../../../components/map/PinMap';
import { ApiError } from '../../../lib/api';
import { errorMessage } from '../../../lib/errorMessage';
import { depthKind, type DetailsValues, type WizardCapture } from './detailsForm';
import { waitText } from './intakeErrors';

interface ReviewStepProps {
  category: Category;
  capture: WizardCapture;
  details: DetailsValues;
  /** The last failed submit that stays on this step (network, server, rate limit). */
  error: unknown;
  submitting: boolean;
  onBack: () => void;
  onSubmit: () => void;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-slate-100 py-2.5 last:border-b-0">
      <dt className="text-sm text-slate-600">{label}</dt>
      <dd className="break-words whitespace-pre-line text-slate-900">{children}</dd>
    </div>
  );
}

function SubmitError({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (error instanceof ApiError && error.code === 'RATE_LIMITED' && error.retryAfterSeconds !== null) {
    const wait = waitText(error.retryAfterSeconds);
    const key = { seconds: 'wizard.rateLimitedSeconds', minutes: 'wizard.rateLimitedMinutes', hours: 'wizard.rateLimitedHours' } as const;
    return <FormAlert>{t(key[wait.unit], { count: wait.count })}</FormAlert>;
  }
  const requestId = error instanceof ApiError && error.code !== 'INTERNAL_ERROR' ? error.requestId : null;
  return (
    <FormAlert>
      <p>{errorMessage(t, error)}</p>
      {requestId !== null && <p className="mt-1 text-xs font-normal">{t('common.reference', { requestId })}</p>}
    </FormAlert>
  );
}

/**
 * Step 4 (docs/05_UI_SPEC.md §4 step 4): photo, read-only map pin from the GPS fix and the typed values. "Send report"
 * is disabled while sending (a double tap cannot send twice; the capture session is single-use anyway, 12 §5).
 */
export function ReviewStep({ category, capture, details, error, submitting, onBack, onSubmit }: ReviewStepProps) {
  const { t } = useTranslation();
  const kind = depthKind(category);
  return (
    <div className="flex flex-col gap-4">
      <p className="text-slate-700">{t('wizard.reviewIntro')}</p>
      <img
        src={capture.url}
        alt={t('wizard.reviewPhoto')}
        className="mx-auto max-h-[45dvh] w-full rounded-2xl bg-slate-200 object-contain"
      />
      <div className="flex flex-col gap-1.5">
        <PinMap lat={capture.lat} lon={capture.lon} label={t('wizard.reviewMap')} />
        <p className="text-sm text-slate-600">{t('wizard.reviewLocation', { meters: Math.round(capture.accuracyM) })}</p>
      </div>
      <dl className="rounded-xl border border-slate-200 bg-white px-4">
        <Row label={t('wizard.reviewCategory')}>{category.name}</Row>
        <Row label={t('wizard.reviewTitle')}>{details.title}</Row>
        <Row label={t('wizard.reviewDescription')}>{details.description}</Row>
        {details.landmark !== '' && <Row label={t('wizard.reviewLandmark')}>{details.landmark}</Row>}
        {category.needsDepthAnswer && details.depthAnswer !== '' && (
          <Row label={t('wizard.reviewDepth')}>{t(`wizard.depth.${kind}${details.depthAnswer}`)}</Row>
        )}
        <Row label={t('wizard.reviewA4')}>{details.a4InFrame ? t('wizard.yes') : t('wizard.no')}</Row>
      </dl>
      {error !== null && <SubmitError error={error} />}
      <div className="grid grid-cols-2 gap-3">
        <button type="button" onClick={onBack} disabled={submitting} data-testid="wizard-back" className={secondaryButtonClass}>
          {t('common.back')}
        </button>
        <button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          data-testid="complaint-submit"
          className={primaryButtonClass}
        >
          {submitting ? t('wizard.submitting') : t('wizard.submit')}
        </button>
      </div>
    </div>
  );
}
