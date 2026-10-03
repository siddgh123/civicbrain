import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Unit/component tests only (docs/08_TEST_PLAN.md §1). Playwright specs live in walkthrough/ and e2e/ and must never
// be collected here (they would run under jsdom and fail).
export default defineConfig({
  plugins: [react()],
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
