import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { createMemoryRouter, parsePath } from 'react-router';
import { App } from '../App';
import { routes } from '../app/routes';
import type { AuthState, Role } from '../auth/authContext';
import { server } from './server';

/** The whole app (providers + routes) at `path`, as a user would open it. */
export function renderApp(path: string, options: { auth?: AuthState; state?: unknown } = {}) {
  const entry = options.state === undefined ? path : { ...parsePath(path), state: options.state };
  const router = createMemoryRouter(routes, { initialEntries: [entry] });
  const user = userEvent.setup();
  const view = render(<App router={router} initialAuth={options.auth} />);
  return { router, user, ...view };
}

export function signedIn(role: Role, overrides: Partial<NonNullable<AuthState['user']>> = {}): AuthState {
  return {
    accessToken: 'test-token',
    user: { id: 7, fullName: 'Asha Patil', role, mustChangePassword: false, preferredLanguage: 'en', ...overrides },
  };
}

export const PROBLEM_HEADERS = { 'Content-Type': 'application/problem+json' };

export function problem(status: number, code: string, extra: Record<string, unknown> = {}) {
  return HttpResponse.json({ status, code, title: code, requestId: 'test-req', ...extra }, { status, headers: PROBLEM_HEADERS });
}

/** GET /public/privacy-notice with a fixed test notice. */
export function mockPrivacyNotice() {
  server.use(
    http.get('/api/v1/public/privacy-notice', () =>
      HttpResponse.json({
        version: '2026-10-v1',
        publishedAt: '2026-10-01T09:00:00+05:30',
        summary: 'Test notice: what CivicBrain stores and why.',
      }),
    ),
  );
}
