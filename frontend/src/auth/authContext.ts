import { createContext } from 'react';

/** Roles that can log in (`user.role` of POST /auth/login, docs/04_API_CONTRACT.md §1). */
export type Role = 'CITIZEN' | 'OFFICER' | 'ADMIN' | 'CONTRACTOR' | 'CONTRACTOR_STAFF';

export interface AuthUser {
  id: number;
  fullName: string;
  role: Role;
  mustChangePassword: boolean;
  preferredLanguage: string;
}

export interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
}

/** `loading` = the silent refresh on page load has not answered yet (guards show a skeleton, never the login page). */
export type AuthStatus = 'loading' | 'signedIn' | 'signedOut';

/** What a successful POST /auth/login led to. `mfa` = the TOTP step (P25, off in the MVP). */
export type LoginOutcome = { kind: 'signedIn'; user: AuthUser } | { kind: 'mfa' };

export interface AuthContextValue extends AuthState {
  status: AuthStatus;
  /** Throws ApiError (INVALID_CREDENTIALS, EMAIL_NOT_VERIFIED with `otpId`, ACCOUNT_LOCKED, RATE_LIMITED …). */
  login: (identifier: string, password: string) => Promise<LoginOutcome>;
  logout: () => Promise<void>;
  /** New access token via the refresh cookie (shared promise); false = signed out. Used after a password change. */
  refreshSession: () => Promise<boolean>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

/** Where each role lands after login and from "Go to my start page". */
export function homePathForRole(role: Role): string {
  switch (role) {
    case 'CITIZEN':
      return '/citizen';
    case 'OFFICER':
    case 'ADMIN':
      return '/officer';
    case 'CONTRACTOR':
    case 'CONTRACTOR_STAFF':
      return '/contractor';
  }
}

const PORTAL_PREFIX: Record<Role, string> = {
  CITIZEN: '/citizen',
  OFFICER: '/officer',
  ADMIN: '/officer',
  CONTRACTOR: '/contractor',
  CONTRACTOR_STAFF: '/contractor',
};

/**
 * Where to go after login: the `returnTo` page when it is a local path this role can open (no open redirect,
 * no other portal), otherwise the role's start page. A forced password change always comes first.
 */
export function pathAfterLogin(user: AuthUser, returnTo: string | null): string {
  if (user.mustChangePassword) return '/change-password';
  if (returnTo === null || !returnTo.startsWith('/') || returnTo.startsWith('//') || returnTo.includes('\\')) {
    return homePathForRole(user.role);
  }
  const portal = ['/citizen', '/officer', '/contractor'].find((p) => returnTo === p || returnTo.startsWith(`${p}/`));
  if (portal !== undefined && portal !== PORTAL_PREFIX[user.role]) return homePathForRole(user.role);
  if (['/login', '/register', '/verify-email', '/change-password'].some((p) => returnTo.startsWith(p))) {
    return homePathForRole(user.role);
  }
  return returnTo;
}
