import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CameraCapture } from '../../components/camera/CameraCapture';
import type { CaptureResult } from '../../components/camera/capture';
import { FormAlert } from '../../components/form/fields';

/**
 * /citizen/new. P07 hosts the photo-and-location step (05 §4 step 2) so the camera and its fallback can be checked;
 * P11 builds the full wizard around it (category, details, review + submit with a capture session).
 */
export function NewComplaintPage() {
  const { t } = useTranslation();
  const [captured, setCaptured] = useState<CaptureResult | null>(null);
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold text-slate-900">{t('pages.citizenNew')}</h1>
        <p className="font-medium text-brand-800">{t('newComplaint.photoStep')}</p>
        <p className="text-sm text-slate-600">{t('newComplaint.wizardNote')}</p>
      </div>
      {captured === null ? (
        <CameraCapture onCapture={setCaptured} />
      ) : (
        <FormAlert tone="success">{t('newComplaint.captured')}</FormAlert>
      )}
    </section>
  );
}
