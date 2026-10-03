import { z } from 'zod';

const claimsSchema = z.object({ mcp: z.boolean().optional() });

/**
 * The `mcp` claim of an access token (must change password, set by the backend while `users.must_change_password`).
 * UX only: the signature is not checked here, the server enforces PASSWORD_CHANGE_REQUIRED on every call.
 */
export function mustChangePasswordClaim(accessToken: string): boolean {
  const payload = accessToken.split('.')[1];
  if (payload === undefined) return false;
  try {
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(payload.length / 4) * 4, '=');
    const parsed = claimsSchema.safeParse(JSON.parse(atob(base64)));
    return parsed.success && parsed.data.mcp === true;
  } catch {
    return false;
  }
}
