import { http, HttpResponse, type RequestHandler } from 'msw';

// Default MSW handlers shared by all tests. Tests add or override their own with `server.use(...)`.
export const handlers: RequestHandler[] = [
  // The app starts with a silent refresh: by default there is no session cookie (signed out).
  http.post('/api/v1/auth/refresh', () =>
    HttpResponse.json(
      { status: 401, code: 'UNAUTHENTICATED', title: 'Unauthenticated', requestId: 'test-refresh' },
      { status: 401, headers: { 'Content-Type': 'application/problem+json' } },
    ),
  ),
  // The citizen home lists the recent complaints (P11): by default the account has none.
  http.get('/api/v1/citizen/complaints', () =>
    HttpResponse.json({ items: [], page: 0, size: 20, totalItems: 0, totalPages: 0 }),
  ),
];
