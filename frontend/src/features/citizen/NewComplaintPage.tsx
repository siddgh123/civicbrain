import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CITIZEN_COMPLAINTS_KEY,
  citizenApi,
  type ComplaintSubmission,
  type SubmitResponse,
} from '../../api/citizenComplaints';
import { CATEGORIES_QUERY_KEY, type Category } from '../../api/publicApi';
import type { CaptureResult } from '../../components/camera/capture';
import { applyServerFieldErrors } from '../../components/form/validation';
import { ApiError } from '../../lib/api';
import { errorMessage } from '../../lib/errorMessage';
import { CategoryStep } from './wizard/CategoryStep';
import {
  DETAILS_DEFAULTS,
  detailsSchema,
  type DetailsInput,
  type DetailsValues,
  type WizardCapture,
} from './wizard/detailsForm';
import { DetailsStep } from './wizard/DetailsStep';
import { DETAIL_FIELDS, intakeErrorTarget } from './wizard/intakeErrors';
import { PhotoStep } from './wizard/PhotoStep';
import { ReviewStep } from './wizard/ReviewStep';
import { SuccessStep } from './wizard/SuccessStep';

type Step = 'category' | 'photo' | 'details' | 'review' | 'done';

const STEP_NUMBER = { category: 1, photo: 2, details: 3, review: 4 } as const;

function submission(category: Category, capture: WizardCapture, details: DetailsValues): ComplaintSubmission {
  return {
    categoryId: category.id,
    title: details.title,
    description: details.description,
    ...(details.landmark !== '' ? { landmark: details.landmark } : {}),
    latitude: capture.lat,
    longitude: capture.lon,
    locationAccuracyM: capture.accuracyM,
    locationCapturedAt: capture.capturedAt,
    ...(capture.pitchDeg !== null ? { devicePitchDeg: capture.pitchDeg } : {}),
    ...(capture.rollDeg !== null ? { deviceRollDeg: capture.rollDeg } : {}),
    captureSessionId: capture.captureSessionId,
    captureMethod: capture.method,
    a4InFrame: details.a4InFrame,
    ...(category.needsDepthAnswer && details.depthAnswer !== '' ? { depthAnswer: details.depthAnswer } : {}),
  };
}

/**
 * `/citizen/new` - the report wizard (docs/05_UI_SPEC.md §4 steps 1-5, FR-10/FR-12): category → photo + location
 * (capture session opened right before the camera) → details → review → multipart submit → CB number. One form
 * instance holds the typed text for the whole wizard, so no error ever loses it; each intake error code sends the
 * citizen to the step that fixes it (docs/12_ERROR_HANDLING.md §2).
 */
export function NewComplaintPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>('category');
  const [category, setCategory] = useState<Category | null>(null);
  const [capture, setCapture] = useState<WizardCapture | null>(null);
  const [details, setDetails] = useState<DetailsValues | null>(null);
  const [photoNotice, setPhotoNotice] = useState<string | null>(null);
  const [categoryNotice, setCategoryNotice] = useState<string | null>(null);
  const [cameraKey, setCameraKey] = useState(0);
  const [reviewError, setReviewError] = useState<unknown>(null);
  const [result, setResult] = useState<SubmitResponse | null>(null);
  const stepHeading = useRef<HTMLParagraphElement | null>(null);
  const firstStep = useRef(true);
  const form = useForm<DetailsInput, unknown, DetailsValues>({
    resolver: zodResolver(detailsSchema),
    defaultValues: DETAILS_DEFAULTS,
    mode: 'onTouched',
  });

  const captureUrl = capture?.url ?? null;
  useEffect(() => {
    if (captureUrl === null) return undefined;
    return () => URL.revokeObjectURL(captureUrl);
  }, [captureUrl]);

  // Each new step starts at its heading (screen readers + the phone scrolls back up).
  useEffect(() => {
    if (firstStep.current) {
      firstStep.current = false;
      return;
    }
    stepHeading.current?.focus();
  }, [step]);

  const openSession = useCallback(async () => (await citizenApi.captureSession()).captureSessionId, []);

  const newCapture = (notice: string | null) => {
    setCapture(null);
    setCameraKey((key) => key + 1);
    setPhotoNotice(notice);
    setStep('photo');
  };

  const submit = useMutation({
    mutationFn: (input: { data: ComplaintSubmission; photo: Blob }) => citizenApi.submit(input.data, input.photo),
    onSuccess: (response) => {
      setResult(response);
      setStep('done');
      void queryClient.invalidateQueries({ queryKey: CITIZEN_COMPLAINTS_KEY });
    },
    onError: (error) => {
      switch (intakeErrorTarget(error)) {
        case 'photo': {
          const ownMessage = error instanceof ApiError && error.code !== 'VALIDATION_FAILED';
          newCapture(ownMessage ? errorMessage(t, error) : t('wizard.photoInvalid'));
          break;
        }
        case 'details':
          // RHF keeps errors of unmounted fields: the details step shows them on its fields when it mounts
          applyServerFieldErrors(error, form.setError, DETAIL_FIELDS);
          setStep('details');
          break;
        case 'category':
          // the category is no longer selectable (V6) or unknown: choose again from a fresh list; the photo and text stay
          setCategoryNotice(t('wizard.categoryNotAllowed'));
          void queryClient.invalidateQueries({ queryKey: CATEGORIES_QUERY_KEY });
          setStep('category');
          break;
        case 'review':
          setReviewError(error);
          break;
      }
    },
  });

  const onCategory = (chosen: Category) => {
    if (category?.id !== chosen.id) form.setValue('depthAnswer', '');
    form.setValue('needsDepth', chosen.needsDepthAnswer);
    setCategory(chosen);
    setCategoryNotice(null);
    // back from a refused category with a photo already taken: straight on to the details
    setStep(categoryNotice !== null && capture !== null ? 'details' : 'photo');
  };

  const onCapture = (captured: CaptureResult) => {
    if (captured.captureSessionId === undefined) return; // openSession is always passed
    setCapture({ ...captured, captureSessionId: captured.captureSessionId, url: URL.createObjectURL(captured.blob) });
    setPhotoNotice(null);
    setStep('details');
  };

  const onDetails = (values: DetailsValues) => {
    setDetails(values);
    setReviewError(null);
    setStep('review');
  };

  const onSubmit = () => {
    if (submit.isPending) return;
    // the review step needs all three; without a photo + location there is nothing to send (09_7DAY §4)
    if (category === null || capture === null || details === null) {
      setStep(category === null ? 'category' : capture === null ? 'photo' : 'details');
      return;
    }
    setReviewError(null);
    submit.mutate({ data: submission(category, capture, details), photo: capture.blob });
  };

  const number = step === 'done' ? null : STEP_NUMBER[step];
  const stepName = { 1: 'wizard.steps.category', 2: 'wizard.steps.photo', 3: 'wizard.steps.details', 4: 'wizard.steps.review' } as const;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-slate-900">{t('pages.citizenNew')}</h1>
        {number !== null && (
          <>
            <p ref={stepHeading} tabIndex={-1} data-testid="wizard-step" className="font-medium text-brand-800 outline-none">
              {t('wizard.stepOf', { step: number, name: t(stepName[number]) })}
            </p>
            <div aria-hidden="true" className="grid grid-cols-4 gap-1.5">
              {[1, 2, 3, 4].map((n) => (
                <span key={n} className={`h-1.5 rounded-full ${n <= number ? 'bg-brand-700' : 'bg-slate-200'}`} />
              ))}
            </div>
          </>
        )}
      </div>

      {step === 'category' && (
        <CategoryStep selectedId={category?.id ?? null} onSelect={onCategory} notice={categoryNotice} />
      )}
      {step === 'photo' && category !== null && (
        <PhotoStep
          category={category}
          capture={capture}
          notice={photoNotice}
          cameraKey={cameraKey}
          openSession={openSession}
          onCapture={onCapture}
          onRetake={() => newCapture(null)}
          onBack={() => setStep('category')}
          onNext={() => setStep('details')}
        />
      )}
      {step === 'details' && category !== null && (
        <DetailsStep form={form} category={category} onBack={() => setStep('photo')} onNext={onDetails} />
      )}
      {step === 'review' && category !== null && capture !== null && details !== null && (
        <ReviewStep
          category={category}
          capture={capture}
          details={details}
          error={reviewError}
          submitting={submit.isPending}
          onBack={() => setStep('details')}
          onSubmit={onSubmit}
        />
      )}
      {step === 'done' && result !== null && <SuccessStep result={result} />}
    </section>
  );
}
