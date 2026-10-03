import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

// App.tsx imports RouterProvider from 'react-router/dom'. Under Vitest the app's 'react-router' imports resolved to the
// CommonJS build while 'react-router/dom' loaded the ESM build → two router contexts. Both entries point to the ESM
// files Node and the browser build use, so there is one React Router copy.
const reactRouterEsm = (file: string) =>
  fileURLToPath(new URL(`./node_modules/react-router/dist/development/${file}`, import.meta.url));

// Unit/component tests only (docs/08_TEST_PLAN.md §1). Playwright specs live in walkthrough/ and e2e/ and must never
// be collected here (they would run under jsdom and fail).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: /^react-router\/dom$/, replacement: reactRouterEsm('dom-export.mjs') },
      { find: /^react-router$/, replacement: reactRouterEsm('index.mjs') },
    ],
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    exclude: ['node_modules', 'e2e', 'walkthrough', 'playwright-report', 'test-results'],
    css: false,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/main.tsx'],
      reporter: ['text-summary', 'html'],
    },
  },
});
