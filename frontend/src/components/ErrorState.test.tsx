import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import en from '../i18n/en.json';
import { ApiError } from '../lib/api';
import { ErrorState } from './ErrorState';

// The 38 codes of docs/12_ERROR_HANDLING.md §2 (= backend common/ErrorCode.java).
const ERROR_CODES = [
  'VALIDATION_FAILED', 'MALFORMED_REQUEST', 'UNAUTHENTICATED', 'INVALID_CREDENTIALS', 'SESSION_REVOKED', 'FORBIDDEN',
  'ROLE_NOT_ALLOWED', 'EMAIL_NOT_VERIFIED', 'MFA_REQUIRED', 'CSRF_CHECK_FAILED', 'NOT_FOUND', 'INVALID_TRANSITION',
  'STALE_VERSION', 'ALREADY_EXISTS', 'COMPLAINT_NOT_PLANNABLE', 'PLAN_STATE_CONFLICT', 'BLUR_NOT_READY',
  'CAPTURE_SESSION_EXPIRED', 'FILE_TOO_LARGE', 'FILE_TYPE_NOT_ALLOWED', 'CAPTURE_SESSION_INVALID',
  'GPS_ACCURACY_TOO_LOW', 'LOCATION_STALE', 'OUTSIDE_BOUNDARY', 'IMAGE_TOO_SMALL', 'IMAGE_TOO_LARGE_PIXELS',
  'OTP_INVALID', 'OTP_EXPIRED', 'OTP_ATTEMPTS_EXCEEDED', 'TOTP_INVALID', 'PASSWORD_POLICY', 'CONTRACTOR_NOT_ELIGIBLE',
  'FEEDBACK_NOT_ALLOWED', 'CONSENT_MISSING', 'ACCOUNT_LOCKED', 'RATE_LIMITED', 'INTERNAL_ERROR',
  'DEPENDENCY_UNAVAILABLE',
];

describe('ErrorState', () => {
  it('en.json has a message for every documented error code', () => {
    const missing = ERROR_CODES.filter((code) => !(code in en.errors));
    expect(missing).toEqual([]);
  });

  it('shows the message for the code, the request id and a working "Try again"', async () => {
    const onRetry = vi.fn();
    const error = new ApiError({ status: 422, code: 'OUTSIDE_BOUNDARY', message: 'server detail', requestId: 'rid-9' });

    render(<ErrorState error={error} onRetry={onRetry} />);

    expect(screen.getByRole('alert')).toHaveTextContent(
      'This location is outside Talegaon Dabhade Municipal Council.',
    );
    expect(screen.getByText('Reference: rid-9')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('puts the request id into the INTERNAL_ERROR message once', () => {
    render(<ErrorState error={new ApiError({ status: 500, code: 'INTERNAL_ERROR', message: 'x', requestId: 'r-500' })} />);

    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong. Reference: r-500');
    expect(screen.getAllByText(/r-500/)).toHaveLength(1);
  });

  it('an unknown code or a plain Error gets the generic message, never the raw text', () => {
    const { unmount } = render(<ErrorState error={new ApiError({ status: 418, code: 'TEAPOT', message: 'raw' })} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong. Please try again.');
    expect(screen.queryByText(/raw/)).not.toBeInTheDocument();
    unmount();

    render(<ErrorState error={new Error('stack trace here')} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong. Please try again.');
    expect(screen.queryByText(/stack trace/)).not.toBeInTheDocument();
  });

  it('RATE_LIMITED uses Retry-After seconds', () => {
    render(<ErrorState error={new ApiError({ status: 429, code: 'RATE_LIMITED', message: 'x', retryAfterSeconds: 42 })} />);
    expect(screen.getByRole('alert')).toHaveTextContent('Please wait 42 seconds and try again.');
  });
});
