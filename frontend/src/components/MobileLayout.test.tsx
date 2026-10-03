import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { getAccessToken } from '../auth/tokenStore';
import { server } from '../test/server';
import { renderApp, signedIn } from '../test/renderApp';

describe('Log out', () => {
  it('from a portal ends on the landing page (not on the login page of that portal) and revokes the cookie', async () => {
    const logoutHeaders: (string | null)[] = [];
    server.use(
      http.post('/api/v1/auth/logout', ({ request }) => {
        logoutHeaders.push(request.headers.get('x-cb-csrf'));
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user, router } = renderApp('/citizen', { auth: signedIn('CITIZEN') });

    await user.click(await screen.findByRole('button', { name: 'Log out' }));

    expect(await screen.findByRole('heading', { level: 1, name: /report civic problems/i })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
    expect(router.state.location.search).toBe('');
    expect(logoutHeaders).toEqual(['1']);
    expect(getAccessToken()).toBeNull();
  });

  it('from the officer portal also ends on the landing page', async () => {
    server.use(http.post('/api/v1/auth/logout', () => new HttpResponse(null, { status: 204 })));
    const { user, router } = renderApp('/officer', { auth: signedIn('OFFICER') });

    await user.click(await screen.findByRole('button', { name: 'Log out' }));

    expect(await screen.findByRole('heading', { level: 1, name: /report civic problems/i })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
  });
});
