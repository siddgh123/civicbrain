import { defineConfig } from '@playwright/test';

// Agent walkthroughs (CLAUDE.md "Browser checks"): the installed Google Chrome, headless, against the stack that
// start-all.ps1 already runs (no webServer). Screenshots go to ../docs/screenshots/. P26's playwright.config.ts uses ./e2e.
export default defineConfig({
  testDir: './walkthrough',
  workers: 1,
  retries: 0,
  reporter: 'line',
  use: { channel: 'chrome', headless: true, baseURL: 'http://localhost:5173' },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
    { name: 'phone', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
  ],
});
