import { expect, test } from '@playwright/test';

// P05 Verify 3: landing page on desktop (1280) and phone (390) + the Vite /api proxy reaches the backend.
// Run (stack up via start-all.ps1): npx playwright test --config playwright.walkthrough.config.ts walkthrough/P05

test('landing page', async ({ page }, testInfo) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    'Report civic problems. Follow them until they are fixed.',
  );
  const main = page.getByRole('main');
  await expect(main.getByRole('link', { name: 'Report a problem' })).toBeVisible();
  await expect(main.getByRole('link', { name: 'Track my complaint' })).toBeVisible();
  await expect(main.getByRole('link', { name: 'Log in' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2, name: 'How it works' })).toBeVisible();

  // No horizontal scrolling at this width.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);

  const name = testInfo.project.name === 'phone' ? 'mobile' : 'desktop';
  await page.screenshot({ path: `../docs/screenshots/P05_landing_${name}.png`, fullPage: true });
});

test('"Report a problem" while signed out goes to the login page with the return URL', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('main').getByRole('link', { name: 'Report a problem' }).click();

  await expect(page).toHaveURL('/login?returnTo=%2Fcitizen%2Fnew');
  await expect(page.getByRole('heading', { level: 1, name: 'Log in' })).toBeVisible();
});

test('/api is proxied to the backend (401/404 problem+json)', async ({ request }) => {
  const response = await request.get('/api/v1/public/categories');

  expect([401, 404]).toContain(response.status());
  expect(response.headers()['content-type']).toContain('application/problem+json');
  expect(response.headers()['x-request-id']).toBeTruthy();
  const body: unknown = await response.json();
  expect(body).toMatchObject({ status: response.status() });
  console.log(`proxy check: ${response.status()} ${JSON.stringify(body)}`);
});
