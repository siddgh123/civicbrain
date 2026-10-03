import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll } from 'vitest';
import '../i18n';
import { clearAccessToken } from '../auth/tokenStore';
import { server } from './server';

// Every request must hit an MSW handler: an unhandled one fails the test instead of reaching the network.
beforeAll(() => server.listen({ onUnhandledFrame: 'error' }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  clearAccessToken();
});
afterAll(() => server.close());
