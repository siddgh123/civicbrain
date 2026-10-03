import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { problem, renderApp } from '../../test/renderApp';

const PASSWORD = 'correct horse battery';

function countLoginCalls() {
  const calls: unknown[] = [];
  server.use(
    http.post('/api/v1/auth/login', async ({ request }) => {
      calls.push(await request.json());
      return problem(401, 'INVALID_CREDENTIALS');
    }),
  );
  return calls;
}

describe('LoginPage', () => {
  it('validates before sending: empty fields, a bad e-mail and a short password never reach the server', async () => {
    const calls = countLoginCalls();
    const { user } = renderApp('/login');
    const submit = await screen.findByRole('button', { name: 'Log in' });

    await user.click(submit);
    expect(screen.getAllByText('Please fill in this field.')).toHaveLength(2);

    await user.type(screen.getByLabelText('E-mail or mobile number'), 'asha@');
    await user.type(screen.getByLabelText('Password'), 'short');
    await user.click(submit);
    expect(await screen.findByText('Enter a valid e-mail address.')).toBeInTheDocument();
    expect(screen.getByText('Use 12 to 128 characters.')).toBeInTheDocument();
    expect(screen.getByLabelText('E-mail or mobile number')).toHaveAttribute('aria-invalid', 'true');

    expect(calls).toHaveLength(0);
  });

  it('accepts a mobile number as identifier and shows the generic error for wrong credentials', async () => {
    const calls = countLoginCalls();
    const { user } = renderApp('/login');

    await user.type(await screen.findByLabelText('E-mail or mobile number'), '98765 43210');
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail/phone or password is incorrect.');
    expect(calls).toEqual([{ identifier: '98765 43210', password: PASSWORD }]);
    // typed data is kept after the error (05 §2)
    expect(screen.getByLabelText('E-mail or mobile number')).toHaveValue('98765 43210');
  });

  it('a citizen lands on the returnTo page after login', async () => {
    server.use(
      http.post('/api/v1/auth/login', () =>
        HttpResponse.json({
          accessToken: 'x.eyJzdWIiOiI3In0.y',
          expiresIn: 900,
          user: { id: 7, fullName: 'Asha Patil', role: 'CITIZEN', mustChangePassword: false, preferredLanguage: 'en' },
        }),
      ),
      http.get('/api/v1/me', () =>
        HttpResponse.json({
          id: 7,
          fullName: 'Asha Patil',
          email: 'asha@example.test',
          phoneMasked: '+91******3210',
          role: 'CITIZEN',
          preferredLanguage: 'en',
          emailOptIn: true,
          whatsappOptIn: false,
          consents: [],
        }),
      ),
    );
    const { user, router } = renderApp('/login?returnTo=%2Fcitizen%2Fprofile');

    await user.type(await screen.findByLabelText('E-mail or mobile number'), 'asha@example.test');
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'My profile' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/citizen/profile');
  });

  it('a one-time password sends the user to the change-password screen first', async () => {
    server.use(
      http.post('/api/v1/auth/login', () =>
        HttpResponse.json({
          accessToken: 'x.eyJtY3AiOnRydWV9.y',
          expiresIn: 900,
          user: { id: 9, fullName: 'Road Works', role: 'CONTRACTOR', mustChangePassword: true, preferredLanguage: 'en' },
        }),
      ),
    );
    const { user, router } = renderApp('/login');

    await user.type(await screen.findByLabelText('E-mail or mobile number'), 'firm@example.test');
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Set a new password' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/change-password');
  });

  it('an unverified e-mail opens the OTP screen with the otpId from the 403 body', async () => {
    server.use(http.post('/api/v1/auth/login', () => problem(403, 'EMAIL_NOT_VERIFIED', { otpId: 41, expiresInSec: 600 })));
    const { user, router } = renderApp('/login');

    await user.type(await screen.findByLabelText('E-mail or mobile number'), 'asha@example.test');
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Enter the code' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/verify-email');
    expect(new URLSearchParams(router.state.location.search).get('otpId')).toBe('41');
    expect(screen.getByText(/We sent a 6-digit code to asha@example.test/)).toBeInTheDocument();
  });
});
