import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './api';

const MAX_QUERY_RETRIES = 2;

/** docs/05_UI_SPEC.md §2: queries (GET) retry twice, never on a 4xx answer. */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_QUERY_RETRIES) return false;
  return !(error instanceof ApiError && error.status >= 400 && error.status < 500);
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetryQuery },
      mutations: { retry: 0 }, // a mutation is never repeated automatically
    },
  });
}
