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

export interface AuthContextValue extends AuthState {
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
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
