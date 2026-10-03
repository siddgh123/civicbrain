import { describe, expect, it } from 'vitest';
import { ApiError } from './api';
import { createQueryClient, shouldRetryQuery } from './queryClient';

const apiError = (status: number) => new ApiError({ status, code: 'X', message: 'x' });

// docs/05_UI_SPEC.md §2: retries only for GET (2 retries, not on 4xx); mutations never auto-retry.
describe('query retry rules', () => {
  it('retries a 5xx / network failure twice, then stops', () => {
    for (const error of [apiError(503), apiError(0), new TypeError('fetch failed')]) {
      expect(shouldRetryQuery(0, error)).toBe(true);
      expect(shouldRetryQuery(1, error)).toBe(true);
      expect(shouldRetryQuery(2, error)).toBe(false);
    }
  });

  it('never retries a 4xx', () => {
    for (const status of [400, 401, 403, 404, 409, 422, 429]) {
      expect(shouldRetryQuery(0, apiError(status))).toBe(false);
    }
  });

  it('mutations do not retry', () => {
    expect(createQueryClient().getDefaultOptions().mutations?.retry).toBe(0);
  });
});
