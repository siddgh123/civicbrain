import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { problem, renderApp } from '../../test/renderApp';

const box = (n: number) => `Digit ${n} of 6`;
const BOXES = [1, 2, 3, 4, 5, 6].map(box);

describe('OtpPage', () => {
  it('accepts a pasted 6-digit code, verifies it and goes to the login with the e-mail filled in', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post('/api/v1/auth/verify-otp', async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json({ verified: true });
      }),
    );
    const { user, router } = renderApp('/verify-email?otpId=41', { state: { email: 'asha@example.test' } });

    await user.click(await screen.findByLabelText(box(1)));
    await user.paste('Code: 123 456');

    expect(BOXES.map((label) => (screen.getByLabelText(label) as HTMLInputElement).value)).toEqual([
      '1', '2', '3', '4', '5', '6',
    ]);
    await user.click(screen.getByRole('button', { name: 'Verify' }));

    expect(await screen.findByText('Your e-mail address is verified. Please log in.')).toBeInTheDocument();
    expect(bodies).toEqual([{ otpId: 41, code: '123456' }]);
    expect(router.state.location.pathname).toBe('/login');
    expect(screen.getByLabelText('E-mail or mobile number')).toHaveValue('asha@example.test');
  });

  it('typing moves box by box; an incomplete code is not sent', async () => {
    let calls = 0;
    server.use(
      http.post('/api/v1/auth/verify-otp', () => {
        calls += 1;
        return HttpResponse.json({ verified: true });
      }),
    );
    const { user } = renderApp('/verify-email?otpId=41');

    await user.click(await screen.findByLabelText(box(1)));
    await user.keyboard('987');
    expect(screen.getByLabelText(box(4))).toHaveFocus();
    await user.click(screen.getByRole('button', { name: 'Verify' }));

    expect(await screen.findByText('Enter all 6 digits.')).toBeInTheDocument();
    expect(calls).toBe(0);
  });

  it('a wrong code shows the matching message; resend waits 60 s', async () => {
    server.use(http.post('/api/v1/auth/verify-otp', () => problem(422, 'OTP_INVALID')));
    const { user } = renderApp('/verify-email?otpId=41');

    expect(await screen.findByRole('button', { name: /Send a new code in \d+ s/ })).toBeDisabled();
    await user.click(screen.getByLabelText(box(1)));
    await user.paste('111111');
    await user.click(screen.getByRole('button', { name: 'Verify' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('The code is incorrect. Check it or request a new one.');
  });

  it('without an otpId the page explains how to get a new code', async () => {
    renderApp('/verify-email');

    expect(await screen.findByText(/This page needs a code request/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute('href', '/register');
  });
});
