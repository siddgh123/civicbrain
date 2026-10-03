import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { RouterProvider, type createBrowserRouter } from 'react-router';
import type { AuthState } from './auth/authContext';
import { AuthProvider } from './auth/AuthProvider';
import { OfflineBanner } from './components/OfflineBanner';
import { ToastProvider } from './components/toast/ToastProvider';
import { createQueryClient } from './lib/queryClient';

export interface AppProps {
  /** `createBrowserRouter(routes)` in the app, `createMemoryRouter(routes, …)` in tests. */
  router: ReturnType<typeof createBrowserRouter>;
  queryClient?: QueryClient;
  /** Tests only (see AuthProvider). */
  initialAuth?: AuthState;
}

export function App({ router, queryClient, initialAuth }: AppProps) {
  const [client] = useState(() => queryClient ?? createQueryClient());
  return (
    <QueryClientProvider client={client}>
      <AuthProvider initialState={initialAuth}>
        <ToastProvider>
          <OfflineBanner />
          <RouterProvider router={router} />
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
