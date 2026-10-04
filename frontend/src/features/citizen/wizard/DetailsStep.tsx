import { useId } from 'react';
import { useWatch, type UseFormReturn } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { DEPTH_ANSWERS, type DepthAnswer } from '../../../api/citizenComplaints';
import type { Category } from '../../../api/publicApi';
import {
  CheckboxField,
  FieldError,
  primaryButtonClass,
  secondaryButtonClass,
  TextAreaField,
  TextField,
} from '../../../components/form/fields';
import {
  depthKind,
  DESCRIPTION_MAX,
  LANDMARK_MAX,
  TITLE_MAX,
  type DetailsInput,
  type DetailsValues,
} from './detailsForm';

interface DetailsStepProps {
  form: UseFormReturn<DetailsInput, unknown, DetailsValues>;
  category: Category;
  onBack: () => void;
  onNext: (values: DetailsValues) => void;
}

const DEPTH_LEVEL: Record<DepthAnswer, 1 | 2 | 3> = { SHALLOW: 1, FINGER: 2, DEEP: 3 };

/** Ground line with a dip of growing depth: the three depth pictograms (05 §4 step 3). */
function DepthPictogram({ level }: { level: 1 | 2 | 3 }) {
  const bottom = 9 + level * 4;
  return (
    <svg viewBox="0 0 48 28" aria-hidden="true" focusable="false" className="h-7 w-12 shrink-0 text-brand-700">
      <path d="M2 8h12M34 8h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none" />
      <path d={`M14 8 Q24 ${bottom * 2 - 8} 34 8`} fill="currentColor" fillOpacity="0.25" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

/**
 * Step 3 (docs/05_UI_SPEC.md §4 step 3): title, description with counters, landmark; the depth question only for
 * categories that need it, with Pothole or Waterlogging labels (sent as SHALLOW / FINGER / DEEP); the A4 toggle.
 */
export function DetailsStep({ form, category, onBack, onNext }: DetailsStepProps) {
  const { t } = useTranslation();
  const depthLegendId = useId();
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = form;
  const [title, description, landmark] = useWatch({ control, name: ['title', 'description', 'landmark'] });
  const kind = depthKind(category);

  return (
    <form noValidate onSubmit={handleSubmit(onNext)} className="flex flex-col gap-5">
      <TextField
        label={t('wizard.titleLabel')}
        hint={t('wizard.titleHint')}
        counter={t('wizard.counter', { count: title.length, max: TITLE_MAX })}
        maxLength={TITLE_MAX}
        autoComplete="off"
        error={errors.title?.message}
        data-testid="complaint-title"
        {...register('title')}
      />
      <TextAreaField
        label={t('wizard.descriptionLabel')}
        hint={t('wizard.descriptionHint')}
        counter={t('wizard.counter', { count: description.length, max: DESCRIPTION_MAX })}
        maxLength={DESCRIPTION_MAX}
        error={errors.description?.message}
        data-testid="complaint-description"
        {...register('description')}
      />
      <TextField
        label={t('wizard.landmarkLabel')}
        hint={t('wizard.landmarkHint')}
        counter={t('wizard.counter', { count: landmark.length, max: LANDMARK_MAX })}
        maxLength={LANDMARK_MAX}
        autoComplete="off"
        error={errors.landmark?.message}
        data-testid="complaint-landmark"
        {...register('landmark')}
      />

      {category.needsDepthAnswer && (
        <div className="flex flex-col gap-2">
          <p id={depthLegendId} className="font-medium text-slate-900">
            {t(`wizard.depth.${kind}Question`)}
          </p>
          <div
            role="radiogroup"
            aria-labelledby={depthLegendId}
            aria-invalid={errors.depthAnswer ? true : undefined}
            className="flex flex-col gap-2"
          >
            {DEPTH_ANSWERS.map((answer) => (
              <label
                key={answer}
                className="flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border-2 border-slate-200 bg-white px-4 py-2 text-slate-900 has-checked:border-brand-700 has-checked:bg-brand-50 has-focus-visible:outline-3 has-focus-visible:outline-offset-2 has-focus-visible:outline-brand-600"
              >
                <input
                  type="radio"
                  value={answer}
                  data-testid={`depth-${answer.toLowerCase()}`}
                  className="size-5 shrink-0 accent-brand-700"
                  {...register('depthAnswer')}
                />
                <DepthPictogram level={DEPTH_LEVEL[answer]} />
                <span className="font-medium">{t(`wizard.depth.${kind}${answer}`)}</span>
              </label>
            ))}
          </div>
          <FieldError id={`${depthLegendId}-error`} message={errors.depthAnswer?.message} />
        </div>
      )}

      <CheckboxField label={t('wizard.a4Label')} data-testid="complaint-a4" {...register('a4InFrame')} />

      <div className="grid grid-cols-2 gap-3">
        <button type="button" onClick={onBack} data-testid="wizard-back" className={secondaryButtonClass}>
          {t('common.back')}
        </button>
        <button type="submit" data-testid="wizard-next" className={primaryButtonClass}>
          {t('wizard.next')}
        </button>
      </div>
    </form>
  );
}
