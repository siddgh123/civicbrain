import { useTranslation } from 'react-i18next';
import type { Category } from '../../../api/publicApi';
import { CameraCapture } from '../../../components/camera/CameraCapture';
import { accuracyTone, type CaptureResult } from '../../../components/camera/capture';
import { FormAlert, primaryButtonClass, secondaryButtonClass } from '../../../components/form/fields';
import { MapPinIcon, RotateIcon } from '../../../components/icons/icons';
import type { WizardCapture } from './detailsForm';

interface PhotoStepProps {
  category: Category;
  capture: WizardCapture | null;
  /** Why a new capture is needed (a submit error such as GPS_ACCURACY_TOO_LOW), shown above the camera. */
  notice: string | null;
  /** A new key mounts a fresh camera (new capture session on the next start). */
  cameraKey: number;
  openSession: () => Promise<string>;
  onCapture: (result: CaptureResult) => void;
  onRetake: () => void;
  onBack: () => void;
  onNext: () => void;
}

const CHIP_TONE = {
  good: 'bg-status-success-bg text-status-success-fg',
  warn: 'bg-status-warning-bg text-status-warning-fg',
  bad: 'bg-status-danger-bg text-status-danger-fg',
  none: 'bg-status-neutral-bg text-status-neutral-fg',
} as const;

/**
 * Step 2 (docs/05_UI_SPEC.md §4 step 2): CameraCapture with the A4 tip for depth categories. Once a photo with a
 * location of 150 m or better exists, it is shown with "Take the photo again" and Next; without it there is no way on.
 */
export function PhotoStep(props: PhotoStepProps) {
  const { category, capture, notice, cameraKey, openSession, onCapture, onRetake, onBack, onNext } = props;
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      {notice !== null && (
        <FormAlert>
          <p>{notice}</p>
          <p className="mt-1 text-sm font-normal">{t('wizard.textKept')}</p>
        </FormAlert>
      )}
      {capture === null ? (
        <CameraCapture key={cameraKey} onCapture={onCapture} openSession={openSession} showA4Tip={category.needsDepthAnswer} />
      ) : (
        <>
          <FormAlert tone="success">{t('wizard.photoReady')}</FormAlert>
          <img
            src={capture.url}
            alt={t('camera.preview')}
            data-testid="wizard-photo"
            className="mx-auto max-h-[50dvh] w-full rounded-2xl bg-slate-200 object-contain"
          />
          <span
            className={`inline-flex items-center gap-1.5 self-start rounded-full px-3 py-1.5 text-sm font-semibold ${CHIP_TONE[accuracyTone(capture.accuracyM)]}`}
          >
            <MapPinIcon className="size-4" />
            {t('camera.gpsAccuracy', { meters: Math.round(capture.accuracyM) })}
          </span>
          <button type="button" onClick={onRetake} data-testid="photo-retake" className={secondaryButtonClass}>
            <RotateIcon className="size-5" />
            {t('wizard.retakePhoto')}
          </button>
        </>
      )}
      <div className="grid grid-cols-2 gap-3">
        <button type="button" onClick={onBack} data-testid="wizard-back" className={secondaryButtonClass}>
          {t('common.back')}
        </button>
        {capture !== null && (
          <button type="button" onClick={onNext} data-testid="wizard-next" className={primaryButtonClass}>
            {t('wizard.next')}
          </button>
        )}
      </div>
    </div>
  );
}
