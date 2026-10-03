import { QueryClientProvider } from '@tanstack/react-query';
import { act, render, screen, waitFor } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import { api } from '../lib/api';
import { createQueryClient } from '../lib/queryClient';
import { server } from '../test/server';
import type { AuthState } from './authContext';
import { AuthProvider } from './AuthProvider';
import { getAccessToken } from './tokenStore';
import { useAuth } from './useAuth';

const PROBLEM = { 'Content-Type': 'application/problem+json' };

/** An unsigned JWT-shaped token with the given payload (the client only reads the `mcp` claim). */
function token(payload: Record<string, unknown>): string {
  return `x.${btoa(JSON.stringify(payload)).replace(/=+$/, '')}.y`;
}

function Probe() {
  const { status, user } = useAuth();
  return (
    <p data-testid="probe">
      {status}:{user === null ? '-' : `${user.fullName}/${user.role}/${String(user.mustChangePassword)}`}
    </p>
  );
}

function renderProvider(initialState?: AuthState) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <AuthProvider initialState={initialState}>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

const SIGNED_IN: AuthState = {
  accessToken: 'old-token',
  user: { id: 7, fullName: 'Asha Patil', role: 'CITIZEN', mustChangePassword: false, preferredLanguage: 'en' },
};

const ME = {
  id: 7,
  fullName: 'Asha Patil',
  email: 'asha@example.test',
  phoneMasked: '+91******3210',
  role: 'CONTRACTOR',
  preferredLanguage: 'en',
  emailOptIn: true,
  whatsappOptIn: false,
  consents: [],
};

describe('AuthProvider', () => {
  it('two parallel 401s trigger ONE refresh, then both calls are retried with the new token', async () => {
    let refreshCalls = 0;
    const csrfHeaders: (string | null)[] = [];
    server.use(
      http.post('/api/v1/auth/refresh', async ({ request }) => {
        refreshCalls += 1;
        csrfHeaders.push(request.headers.get('x-cb-csrf'));
        await delay(20);
        return HttpResponse.json({ accessToken: 'new-token', expiresIn: 900 });
      }),
      http.get('/api/v1/citizen/:name', ({ request, params }) =>
        request.headers.get('authorization') === 'Bearer new-token'
          ? HttpResponse.json({ name: params.name })
          : HttpResponse.json({ status: 401, code: 'UNAUTHENTICATED' }, { status: 401, headers: PROBLEM }),
      ),
    );
    renderProvider(SIGNED_IN);
    const schema = z.object({ name: z.string() });

    const results = await Promise.all([api.get('/citizen/a', schema), api.get('/citizen/b', schema)]);

    expect(results).toEqual([{ name: 'a' }, { name: 'b' }]);
    expect(refreshCalls).toBe(1);
    expect(csrfHeaders).toEqual(['1']);
    expect(getAccessToken()).toBe('new-token');
  });

  it('a failed refresh signs out and the original 401 reaches the caller (no second retry)', async () => {
    let calls = 0;
    server.use(
      http.get('/api/v1/me', () => {
        calls += 1;
        return HttpResponse.json({ status: 401, code: 'UNAUTHENTICATED' }, { status: 401, headers: PROBLEM });
      }),
    );
    renderProvider(SIGNED_IN);

    await expect(api.get('/me', z.unknown())).rejects.toMatchObject({ code: 'UNAUTHENTICATED' });
    expect(calls).toBe(1);
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('signedOut:-'));
    expect(getAccessToken()).toBeNull();
  });

  it('on page load the silent refresh restores the session (user from GET /me, mcp claim from the token)', async () => {
    const restored = token({ sub: '7', mcp: true });
    server.use(
      http.post('/api/v1/auth/refresh', () => HttpResponse.json({ accessToken: restored, expiresIn: 900 })),
      http.get('/api/v1/me', ({ request }) =>
        request.headers.get('authorization') === `Bearer ${restored}`
          ? HttpResponse.json(ME)
          : HttpResponse.json({ status: 401, code: 'UNAUTHENTICATED' }, { status: 401, headers: PROBLEM }),
      ),
    );
    renderProvider();

    expect(screen.getByTestId('probe')).toHaveTextContent('loading:-');
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('signedIn:Asha Patil/CONTRACTOR/true'));
    expect(getAccessToken()).toBe(restored);
  });

  it('on page load without a session cookie the user is signed out', async () => {
    renderProvider();

    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('signedOut:-'));
  });

  it('a logout in another tab (BroadcastChannel cb-auth) signs this tab out', async () => {
    renderProvider(SIGNED_IN);
    expect(screen.getByTestId('probe')).toHaveTextContent('signedIn:Asha Patil');

    const otherTab = new BroadcastChannel('cb-auth');
    await act(async () => {
      otherTab.postMessage({ type: 'logout' });
      await delay(20);
    });
    otherTab.close();

    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('signedOut:-'));
    expect(getAccessToken()).toBeNull();
  });
});
