import { z } from 'zod';
import { api } from '../lib/api';

// /auth (docs/04_API_CONTRACT.md §1). Refresh and logout carry the `__Host-cb_rt` cookie and the CSRF header
// (docs/07_SECURITY.md §1); every other call is a plain JSON POST.

const COOKIE_CALL = { credentials: 'include', headers: { 'X-CB-CSRF': '1' } } as const;

export const roleSchema = z.enum(['CITIZEN', 'OFFICER', 'ADMIN', 'CONTRACTOR', 'CONTRACTOR_STAFF']);

export const userSummarySchema = z.object({
  id: z.number(),
  fullName: z.string(),
  role: roleSchema,
  mustChangePassword: z.boolean(),
  preferredLanguage: z.string(),
});

const tokenSchema = z.object({ accessToken: z.string().min(1), expiresIn: z.number() });

/** 200 of POST /auth/login: tokens + user, or a TOTP step (only when MFA is switched on, P25). */
export const loginResponseSchema = z.union([
  tokenSchema.extend({ user: userSummarySchema }),
  z.object({ mfaRequired: z.literal(true), mfaToken: z.string() }),
  z.object({ mfaSetupRequired: z.literal(true), mfaToken: z.string() }),
]);
export type LoginResponse = z.output<typeof loginResponseSchema>;

export const otpResponseSchema = z.object({ otpId: z.number(), expiresInSec: z.number() });
export type OtpResponse = z.output<typeof otpResponseSchema>;

/** Extension members of 403 EMAIL_NOT_VERIFIED (`expiresInSec` is absent when the newest code is reused). */
export const emailNotVerifiedSchema = z.object({ otpId: z.number(), expiresInSec: z.number().optional() });

export interface RegisterBody {
  fullName: string;
  email: string;
  phone: string;
  password: string;
  privacyNoticeVersion: string;
  consents: { whatsapp: boolean; publicPhoto: boolean; aiTraining: boolean };
}

export const authApi = {
  login: (identifier: string, password: string) => api.post('/auth/login', loginResponseSchema, { identifier, password }),
  refresh: () => api.post('/auth/refresh', tokenSchema, undefined, COOKIE_CALL),
  logout: () => api.post('/auth/logout', null, undefined, COOKIE_CALL),
  register: (body: RegisterBody) => api.post('/auth/register', otpResponseSchema, body),
  verifyOtp: (otpId: number, code: string) =>
    api.post('/auth/verify-otp', z.object({ verified: z.literal(true) }), { otpId, code }),
  resendOtp: (otpId: number) => api.post('/auth/resend-otp', null, { otpId }),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/password/change', null, { currentPassword, newPassword }),
};
