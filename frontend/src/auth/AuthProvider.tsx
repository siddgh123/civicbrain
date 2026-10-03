import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { AuthContext, type AuthContextValue, type AuthState } from './authContext';
import { clearAccessToken, setAccessToken } from './tokenStore';

const SIGNED_OUT: AuthState = { user: null, accessToken: null };

interface AuthProviderProps {
  children: ReactNode;
  /** Tests only: start signed in. The app always starts signed out (P07 restores the session via refresh). */
  initialState?: AuthState;
}

/**
 * Placeholder (P05): holds `{user, accessToken}` in memory only. P07 completes it: real login (POST /auth/login),
 * silent refresh on load with one shared refresh promise, logout via POST /auth/logout and BroadcastChannel('cb-auth').
 */
export function AuthProvider({ children, initialState }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>(() => {
    const start = initialState ?? SIGNED_OUT;
    setAccessToken(start.accessToken);
    return start;
  });

  const login = useCallback(async (): Promise<void> => {
    throw new Error('Login is implemented in P07');
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    clearAccessToken();
    setState(SIGNED_OUT);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({ ...state, login, logout }), [state, login, logout]);
  return <AuthContext value={value}>{children}</AuthContext>;
}
