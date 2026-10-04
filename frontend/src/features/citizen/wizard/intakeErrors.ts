import { ApiError } from '../../../lib/api';

/** The wizard step where the citizen can fix a failed submit (docs/12_ERROR_HANDLING.md §2 intake codes). */
export type WizardTarget = 'category' | 'photo' | 'details' | 'review';

/** Codes that need a new photo + location (and so a new capture session). */
const PHOTO_CODES = new Set([
  'CAPTURE_SESSION_INVALID',
  'CAPTURE_SESSION_EXPIRED',
  'GPS_ACCURACY_TOO_LOW',
  'LOCATION_STALE',
  'OUTSIDE_BOUNDARY',
  'FILE_TOO_LARGE',
  'FILE_TYPE_NOT_ALLOWED',
  'IMAGE_TOO_SMALL',
  'IMAGE_TOO_LARGE_PIXELS',
]);

/** Fields of the details step (`data` keys of 04 §5). */
export const DETAIL_FIELDS = ['title', 'description', 'landmark', 'depthAnswer', 'a4InFrame'] as const;

const PHOTO_FIELDS = new Set([
  'latitude',
  'longitude',
  'locationAccuracyM',
  'locationCapturedAt',
  'devicePitchDeg',
  'deviceRollDeg',
  'captureSessionId',
  'captureMethod',
  'photo',
]);

function isDetailField(field: string): boolean {
  return (DETAIL_FIELDS as readonly string[]).includes(field);
}

/**
 * Where a failed submit sends the citizen: a new capture for session / location / photo problems, the details step for
 * its own field errors (typed data is kept there), the category step for a bad category, otherwise the review step
 * (send again: network, server, rate limit).
 */
export function intakeErrorTarget(error: unknown): WizardTarget {
  if (!(error instanceof ApiError)) return 'review';
  if (PHOTO_CODES.has(error.code)) return 'photo';
  if (error.code !== 'VALIDATION_FAILED') return 'review';
  const fields = error.fieldErrors.map((item) => item.field);
  if (fields.some(isDetailField)) return 'details';
  if (fields.includes('categoryId')) return 'category';
  if (fields.some((field) => PHOTO_FIELDS.has(field))) return 'photo';
  return 'review';
}

/** Retry-After as words: the 5-per-24-h limit can mean hours (04 §11). */
export function waitText(seconds: number): { unit: 'seconds' | 'minutes' | 'hours'; count: number } {
  if (seconds <= 120) return { unit: 'seconds', count: seconds };
  if (seconds < 7200) return { unit: 'minutes', count: Math.ceil(seconds / 60) };
  return { unit: 'hours', count: Math.ceil(seconds / 3600) };
}
