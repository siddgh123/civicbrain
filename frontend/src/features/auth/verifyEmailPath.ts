/** Router state of the OTP screen: the e-mail is shown in the text only (memory, never in the URL). */
export interface VerifyEmailState {
  email?: string;
}

/** `/verify-email?otpId=…` (the otpId is not secret; it survives a reload). `returnTo` is passed on to the login. */
export function verifyEmailPath(otpId: number, returnTo: string | null): string {
  const params = new URLSearchParams({ otpId: String(otpId) });
  if (returnTo !== null) params.set('returnTo', returnTo);
  return `/verify-email?${params.toString()}`;
}
