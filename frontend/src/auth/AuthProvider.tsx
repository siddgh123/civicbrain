import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { z } from 'zod';
import { authApi } from '../api/auth';
import { meApi } from '../api/me';
import { ApiError, setRefreshHandler } from '../lib/api';
import {
  AuthContext,
  type AuthContextValue,
  type AuthState,
  type AuthStatus,
  type AuthUser,
  type LoginOutcome,
} from './authContext';
import { mustChangePasswordClaim } from './jwt';
import { clearAccessToken, setAccessToken } from './tokenStore';

const CHANNEL_NAME = 'cb-auth';
const REFRESH_LOCK = 'cb-auth-refresh';
const channelMessageSchema = z.object({ type: z.literal('logout') });

interface ProviderState extends AuthState {
  status: AuthStatus;
}

const SIGNED_OUT: ProviderState = { status: 'signedOut', user: null, accessToken: null };

/**
 * Refresh tokens rotate and a reused one revokes the whole family (docs/07_SECURITY.md §1), so two tabs must never
 * send the same cookie at once: the Web Locks API runs one refresh at a time per browser (the second tab then sends
 * the already rotated cookie). Inside one tab the shared promise below does the same.
 */
function withRefreshLock<T>(task: () => Promise<T>): Promise<T> {
  if (typeof navigator !== 'undefined' && 'locks' in navigator && navigator.locks !== undefined) {
    return navigator.locks.request(REFRESH_LOCK, task);
  }
  return task();
}

function openChannel(): BroadcastChannel | null {
  return typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(CHANNEL_NAME);
}

interface AuthProviderProps {
  children: ReactNode;
  /** Tests only: start in this state without the silent refresh. The app starts with the refresh. */
  initialState?: AuthState;
}

/**
 * docs/05_UI_SPEC.md §2 Auth + rule 20: the access token lives in memory only; on page load one silent
 * `POST /auth/refresh` (cookie + `X-CB-CSRF: 1`) restores the session; parallel 401s share ONE refresh promise;
 * logout is synced to the other tabs with `BroadcastChannel('cb-auth')`.
 */
export function AuthProvider({ children, initialState }: AuthProviderProps) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<ProviderState>(() => {
    if (initialState === undefined) return { status: 'loading', user: null, accessToken: null };
    setAccessToken(initialState.accessToken);
    return { ...initialState, status: initialState.user === null ? 'signedOut' : 'signedIn' };
  });
  const userRef = useRef<AuthUser | null>(state.user);
  const refreshing = useRef<Promise<boolean> | null>(null);
  const channel = useRef<BroadcastChannel | null>(null);
  // Bumped on every sign-out, so a refresh that was already running cannot sign the user back in afterwards.
  const generation = useRef(0);

  const signedIn = useCallback((user: AuthUser, accessToken: string) => {
    setAccessToken(accessToken);
    userRef.current = user;
    setState({ status: 'signedIn', user, accessToken });
  }, []);

  const signOutLocally = useCallback(() => {
    generation.current += 1;
    clearAccessToken();
    userRef.current = null;
    queryClient.clear(); // no personal data of the old session stays in the cache
    setState(SIGNED_OUT);
  }, [queryClient]);

  const runRefresh = useCallback(async (): Promise<boolean> => {
    const started = generation.current;
    try {
      const { accessToken } = await withRefreshLock(() => authApi.refresh());
      if (generation.current !== started) return false;
      setAccessToken(accessToken);
      const mustChangePassword = mustChangePasswordClaim(accessToken);
      const known = userRef.current;
      if (known !== null) {
        signedIn({ ...known, mustChangePassword }, accessToken);
        return true;
      }
      // The refresh answer has no user: name, role and language come from GET /me (allowed even with `mcp`).
      const me = await meApi.get({ noRefresh: true });
      if (generation.current !== started) return false;
      signedIn(
        { id: me.id, fullName: me.fullName, role: me.role, preferredLanguage: me.preferredLanguage, mustChangePassword },
        accessToken,
      );
      return true;
    } catch (error) {
      if (generation.current !== started) return false;
      // Offline or server down during a session: keep the user signed in, the call simply fails (retry later).
      const transient = error instanceof ApiError && (error.status === 0 || error.status >= 500);
      if (!(transient && userRef.current !== null)) signOutLocally();
      return false;
    }
  }, [signedIn, signOutLocally]);

  const refreshSession = useCallback((): Promise<boolean> => {
    refreshing.current ??= runRefresh().finally(() => {
      refreshing.current = null;
    });
    return refreshing.current;
  }, [runRefresh]);

  const login = useCallback(
    async (identifier: string, password: string): Promise<LoginOutcome> => {
      const response = await authApi.login(identifier, password);
      if (!('accessToken' in response)) return { kind: 'mfa' };
      queryClient.clear();
      signedIn(response.user, response.accessToken);
      return { kind: 'signedIn', user: response.user };
    },
    [queryClient, signedIn],
  );

  const logout = useCallback(async (): Promise<void> => {
    signOutLocally();
    channel.current?.postMessage({ type: 'logout' });
    try {
      await authApi.logout();
    } catch {
      // Already signed out here; the server revokes the family on its own expiry.
    }
  }, [signOutLocally]);

  useEffect(() => {
    setRefreshHandler(refreshSession);
    return () => setRefreshHandler(null);
  }, [refreshSession]);

  useEffect(() => {
    const opened = openChannel();
    channel.current = opened;
    if (opened === null) return undefined;
    opened.onmessage = (event: MessageEvent<unknown>) => {
      if (channelMessageSchema.safeParse(event.data).success) signOutLocally();
    };
    return () => {
      opened.close();
      channel.current = null;
    };
  }, [signOutLocally]);

  const startedLoading = useRef(false);
  useEffect(() => {
    if (initialState !== undefined || startedLoading.current) return;
    startedLoading.current = true;
    void refreshSession();
  }, [initialState, refreshSession]);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, login, logout, refreshSession }),
    [state, login, logout, refreshSession],
  );
  return <AuthContext value={value}>{children}</AuthContext>;
}
