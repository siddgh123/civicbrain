import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { problem, renderApp, signedIn } from '../../test/renderApp';

describe('ChangePasswordPage', () => {
  it('mustChangePassword: every portal page redirects here first', async () => {
    const { router } = renderApp('/contractor', { auth: signedIn('CONTRACTOR', { mustChangePassword: true }) });

    expect(await screen.findByRole('heading', { level: 1, name: 'Set a new password' })).toBeInTheDocument();
    expect(screen.getByText(/You signed in with a one-time password/)).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/change-password');
  });

  it('after the change the session is refreshed (old token revoked) and the user goes to the portal', async () => {
    let refreshed = 0;
    server.use(
      http.post('/api/v1/auth/password/change', () => new HttpResponse(null, { status: 204 })),
      http.post('/api/v1/auth/refresh', () => {
        refreshed += 1;
        return HttpResponse.json({ accessToken: 'x.eyJzdWIiOiI5In0.y', expiresIn: 900 });
      }),
    );
    const { user, router } = renderApp('/change-password', {
      auth: signedIn('CONTRACTOR', { mustChangePassword: true }),
    });

    await user.type(await screen.findByLabelText('Current password'), 'one-time-password-1');
    await user.type(screen.getByLabelText('New password'), 'my own long password');
    await user.type(screen.getByLabelText('Repeat the new password'), 'my own long password');
    await user.click(screen.getByRole('button', { name: 'Save new password' }));

    expect(await screen.findByRole('heading', { level: 1, name: "Today's work" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/contractor');
    expect(refreshed).toBe(1);
  });

  it('a wrong current password is shown on that field; mismatching new passwords are caught first', async () => {
    let calls = 0;
    server.use(
      http.post('/api/v1/auth/password/change', () => {
        calls += 1;
        return problem(400, 'VALIDATION_FAILED', {
          fieldErrors: [{ field: 'currentPassword', code: 'INCORRECT', message: 'is not correct' }],
        });
      }),
    );
    const { user } = renderApp('/change-password', { auth: signedIn('CITIZEN') });

    await user.type(await screen.findByLabelText('Current password'), 'not the password');
    await user.type(screen.getByLabelText('New password'), 'my own long password');
    await user.type(screen.getByLabelText('Repeat the new password'), 'my own long passwort');
    await user.click(screen.getByRole('button', { name: 'Save new password' }));
    expect(await screen.findByText('The two passwords are not the same.')).toBeInTheDocument();
    expect(calls).toBe(0);

    await user.clear(screen.getByLabelText('Repeat the new password'));
    await user.type(screen.getByLabelText('Repeat the new password'), 'my own long password');
    await user.click(screen.getByRole('button', { name: 'Save new password' }));

    expect(await screen.findByText('This is not correct.')).toBeInTheDocument();
    expect(screen.getByLabelText('Current password')).toHaveAttribute('aria-invalid', 'true');
    expect(calls).toBe(1);
  });
});
