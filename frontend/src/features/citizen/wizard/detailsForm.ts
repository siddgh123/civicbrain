import { z } from 'zod';
import { DEPTH_ANSWERS } from '../../../api/citizenComplaints';
import type { Category } from '../../../api/publicApi';
import type { CaptureResult } from '../../../components/camera/capture';
import { hasControlChars } from '../../../components/form/validation';

// Step 3 mirrors the backend ComplaintData (docs/04 §5, FR-10 lengths): title 5-120, description 10-1000 (line
// breaks allowed), landmark ≤ 200, no control characters; the depth answer is required only when the category
// asks for it (`needsDepth` is set by the wizard when the category is chosen).

export const TITLE_MAX = 120;
export const DESCRIPTION_MAX = 1000;
export const LANDMARK_MAX = 200;

const noControl = (value: string) => !hasControlChars(value);
const noControlExceptLineBreaks = (value: string) => !hasControlChars(value.replace(/[\t\n\r]/g, ''));

export const detailsSchema = z
  .object({
    title: z.string().trim().min(5, 'titleLength').max(TITLE_MAX, 'titleLength').refine(noControl, 'controlChars'),
    description: z
      .string()
      .trim()
      .min(10, 'descriptionLength')
      .max(DESCRIPTION_MAX, 'descriptionLength')
      .refine(noControlExceptLineBreaks, 'controlChars'),
    landmark: z.string().trim().max(LANDMARK_MAX, 'tooLong').refine(noControl, 'controlChars'),
    depthAnswer: z.enum(['', ...DEPTH_ANSWERS]),
    a4InFrame: z.boolean(),
    needsDepth: z.boolean(),
  })
  .superRefine((values, ctx) => {
    if (values.needsDepth && values.depthAnswer === '') {
      ctx.addIssue({ code: 'custom', path: ['depthAnswer'], message: 'depthRequired' });
    }
  });

export type DetailsInput = z.input<typeof detailsSchema>;
export type DetailsValues = z.output<typeof detailsSchema>;

export const DETAILS_DEFAULTS: DetailsInput = {
  title: '',
  description: '',
  landmark: '',
  depthAnswer: '',
  a4InFrame: false,
  needsDepth: false,
};

/** A photo + location from CameraCapture with its capture session and a preview URL (revoked by the wizard). */
export interface WizardCapture extends CaptureResult {
  captureSessionId: string;
  url: string;
}

/** Waterlogging asks about water depth (ankle / knee), every other depth category about a finger (05 §4 step 3). */
export function depthKind(category: Category): 'water' | 'pothole' {
  return category.name === 'Waterlogging' ? 'water' : 'pothole';
}
