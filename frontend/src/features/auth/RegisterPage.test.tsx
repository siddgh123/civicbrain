import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { mockPrivacyNotice, problem, renderApp } from '../../test/renderApp';

function recordRegister(answer: () => Response = () => HttpResponse.json({ otpId: 99, expiresInSec: 600 }, { status: 202 })) {
  const bodies: unknown[] = [];
  server.use(
    http.post('/api/v1/auth/register', async ({ request }) => {
      bodies.push(await request.json());
      return answer();
    }),
  );
  return bodies;
}

async function fillValidForm(user: ReturnType<typeof renderApp>['user']) {
  await user.type(await screen.findByLabelText('Full name'), 'Asha Patil');
  await user.type(screen.getByLabelText('E-mail'), 'asha@example.test');
  await user.type(screen.getByLabelText('Mobile number'), '9876543210');
  await user.type(screen.getByLabelText('Password'), 'a long and private sentence');
}

describe('RegisterPage', () => {
  it('requires the privacy checkbox: nothing is sent until the notice is accepted', async () => {
    mockPrivacyNotice();
    const bodies = recordRegister();
    const { user } = renderApp('/register');
    expect(await screen.findByText('Test notice: what CivicBrain stores and why.')).toBeInTheDocument();
    expect(screen.getByText(/Version 2026-10-v1/)).toBeInTheDocument();

    await fillValidForm(user);
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText('Please accept the privacy notice to create an account.')).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('sends +91 phone, the notice version and the optional consents, then opens the OTP screen', async () => {
    mockPrivacyNotice();
    const bodies = recordRegister();
    const { user, router } = renderApp('/register');

    await fillValidForm(user);
    await user.click(screen.getByLabelText('I have read the privacy notice and I accept it.'));
    await user.click(screen.getByLabelText('Send me WhatsApp updates about my complaints'));
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Enter the code' })).toBeInTheDocument();
    expect(bodies).toEqual([
      {
        fullName: 'Asha Patil',
        email: 'asha@example.test',
        phone: '+919876543210',
        password: 'a long and private sentence',
        privacyNoticeVersion: '2026-10-v1',
        consents: { whatsapp: true, publicPhoto: false, aiTraining: false },
      },
    ]);
    expect(new URLSearchParams(router.state.location.search).get('otpId')).toBe('99');
  });

  it('a server PASSWORD_POLICY field error is shown on the password field, typed data stays', async () => {
    mockPrivacyNotice();
    recordRegister(() =>
      problem(422, 'PASSWORD_POLICY', {
        fieldErrors: [{ field: 'password', code: 'PASSWORD_POLICY', message: 'This password is too common.' }],
      }),
    );
    const { user } = renderApp('/register');

    await fillValidForm(user);
    await user.click(screen.getByLabelText('I have read the privacy notice and I accept it.'));
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByText(/This password is not allowed/)).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Full name')).toHaveValue('Asha Patil');
  });
});
