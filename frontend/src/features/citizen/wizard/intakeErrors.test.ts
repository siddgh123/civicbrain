import { describe, expect, it } from 'vitest';
import { ApiError } from '../../../lib/api';
import { intakeErrorTarget, waitText } from './intakeErrors';

// docs/12 §2 intake codes: every code leads to the step where the citizen can fix it (prompt P11 Build 1).

function apiError(code: string, status = 422, fields: string[] = []) {
  return new ApiError({
    status,
    code,
    message: code,
    fieldErrors: fields.map((field) => ({ field, code: 'INVALID_VALUE', message: 'x' })),
  });
}

describe('intakeErrorTarget', () => {
  it.each([
    ['CAPTURE_SESSION_INVALID', 422],
    ['CAPTURE_SESSION_EXPIRED', 410],
    ['GPS_ACCURACY_TOO_LOW', 422],
    ['LOCATION_STALE', 422],
    ['OUTSIDE_BOUNDARY', 422],
    ['FILE_TOO_LARGE', 413],
    ['FILE_TYPE_NOT_ALLOWED', 415],
    ['IMAGE_TOO_SMALL', 422],
    ['IMAGE_TOO_LARGE_PIXELS', 422],
  ])('%s → capture again (step 2)', (code, status) => {
    expect(intakeErrorTarget(apiError(code, status))).toBe('photo');
  });

  it('VALIDATION_FAILED goes to the step that owns the field', () => {
    expect(intakeErrorTarget(apiError('VALIDATION_FAILED', 400, ['title']))).toBe('details');
    expect(intakeErrorTarget(apiError('VALIDATION_FAILED', 400, ['depthAnswer']))).toBe('details');
    expect(intakeErrorTarget(apiError('VALIDATION_FAILED', 400, ['landmark', 'latitude']))).toBe('details');
    expect(intakeErrorTarget(apiError('VALIDATION_FAILED', 400, ['categoryId']))).toBe('category');
    expect(intakeErrorTarget(apiError('VALIDATION_FAILED', 400, ['latitude']))).toBe('photo');
    expect(intakeErrorTarget(apiError('VALIDATION_FAILED', 400, ['photo']))).toBe('photo');
    expect(intakeErrorTarget(apiError('VALIDATION_FAILED', 400, ['data']))).toBe('review');
  });

  it.each(['RATE_LIMITED', 'NETWORK_ERROR', 'INTERNAL_ERROR', 'DEPENDENCY_UNAVAILABLE', 'MALFORMED_REQUEST'])(
    '%s stays on the review step (send again)',
    (code) => {
      expect(intakeErrorTarget(apiError(code, 500))).toBe('review');
    },
  );

  it('anything that is not an ApiError stays on the review step', () => {
    expect(intakeErrorTarget(new Error('boom'))).toBe('review');
  });
});

describe('waitText', () => {
  it('says seconds, minutes or hours', () => {
    expect(waitText(45)).toEqual({ unit: 'seconds', count: 45 });
    expect(waitText(600)).toEqual({ unit: 'minutes', count: 10 });
    expect(waitText(601)).toEqual({ unit: 'minutes', count: 11 });
    expect(waitText(80_000)).toEqual({ unit: 'hours', count: 23 });
  });
});
