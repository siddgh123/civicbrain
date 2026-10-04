import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';

// P11 Verify 2 on the freshly seeded E2E stack (start-all.ps1 -E2E), logged in as ui.citizen:
// empty list of the new account → wizard steps 1-4 with the camera fallback + tests/fixtures/images/pothole_1.jpg at
// the location 18.7440, 73.6760 (inside TDMC) → submit → CB number → list → detail; then a second report from
// 18.7700, 73.7500 (inside the API's lat/lon box, outside TDMC - the smoke test's point) → OUTSIDE_BOUNDARY message.
// Run the phone project first (it screenshots and expects the empty list), then desktop:
//   npx playwright test --config playwright.walkthrough.config.ts walkthrough/P11 --project phone
// The ui.citizen password is read from the git-ignored accounts file at run time and never printed or screenshotted.
// OSM tiles are blocked (the agent's browser stays on localhost); the map shows the pin and the credit on grey.
// Location: Playwright's geolocation grant never answers in headless Chrome on the build laptop (a direct
// getCurrentPosition → error 3 "Timeout expired", desktop and phone projects, P11 log), so an init script replaces
// navigator.geolocation with a fixed position. No camera: the wizard uses the file fallback. Real GPS + camera = P13.

const ACCOUNTS_FILE = new URL('../../tests/e2e-ui-accounts.local.json', import.meta.url);
const POTHOLE_PHOTO = fileURLToPath(new URL('../../tests/fixtures/images/pothole_1.jpg', import.meta.url));
const INSIDE_TDMC = { latitude: 18.744, longitude: 73.676, accuracy: 12 };
const OUTSIDE_TDMC = { latitude: 18.77, longitude: 73.75, accuracy: 12 };

type Fix = typeof INSIDE_TDMC;

// Full-page screenshots draw a sticky/fixed bar where the viewport was, on top of the content of a long page. For a
// page taller than the screen, only while the screenshot is taken, the top bar and the bottom navigation are put into
// the normal page flow (a short page is captured as it is: the bottom navigation sits at the bottom of the screen).
const FULL_PAGE_STYLE = [
  'header, nav[aria-label="Main navigation"] { position: static !important; }',
  'div:has(> nav[aria-label="Main navigation"]) { padding-bottom: 0 !important; }',
].join('\n');

/** Every page opened after this answers geolocation with `fix` (a later call wins: init scripts run in order). */
async function useFakeGps(context: BrowserContext, fix: Fix) {
  await context.addInitScript((f: Fix) => {
    const position = (): GeolocationPosition =>
      ({
        coords: { latitude: f.latitude, longitude: f.longitude, accuracy: f.accuracy },
        timestamp: Date.now(),
      }) as GeolocationPosition;
    const geolocation = {
      getCurrentPosition: (ok: PositionCallback) => void setTimeout(() => ok(position()), 100),
      watchPosition: (ok: PositionCallback) => {
        setTimeout(() => ok(position()), 100);
        return window.setInterval(() => ok(position()), 2000);
      },
      clearWatch: (id: number) => window.clearInterval(id),
    };
    Object.defineProperty(Navigator.prototype, 'geolocation', { get: () => geolocation, configurable: true });
  }, fix);
}

function uiCitizen(): { email: string; password: string } {
  // trim() also drops a byte-order mark that PowerShell may write
  const parsed: unknown = JSON.parse(readFileSync(ACCOUNTS_FILE, 'utf8').trim());
  if (typeof parsed === 'object' && parsed !== null && 'citizen' in parsed) {
    const citizen: unknown = parsed.citizen;
    if (typeof citizen === 'object' && citizen !== null && 'email' in citizen && 'password' in citizen) {
      const { email, password } = citizen;
      if (typeof email === 'string' && typeof password === 'string') return { email, password };
    }
  }
  throw new Error('tests/e2e-ui-accounts.local.json has no citizen account (run seed-e2e.ps1)');
}

async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

/** Steps 1-3: Pothole → fallback photo → details. */
async function wizardToReview(page: Page, title: string, shot: (name: string) => Promise<void>) {
  await page.goto('/citizen/new');
  await expect(page.getByTestId('wizard-step')).toHaveText('Step 1 of 4: Category');
  await expect(page.getByRole('button', { name: 'Pothole' })).toBeVisible();
  await expectNoHorizontalScroll(page);
  await shot('P11_wizard_1_category');
  await page.getByRole('button', { name: 'Pothole' }).click();

  await expect(page.getByTestId('wizard-step')).toHaveText('Step 2 of 4: Photo and location');
  await expect(page.getByText('Optional: place an A4 sheet next to it')).toBeVisible();
  await page.getByTestId('capture-start').click();
  await expect(page.getByRole('heading', { name: 'The camera could not be opened' })).toBeVisible();
  await expectNoHorizontalScroll(page);
  await shot('P11_wizard_2_camera_fallback');
  await page.getByTestId('capture-file').setInputFiles(POTHOLE_PHOTO);
  await expect(page.getByTestId('capture-preview')).toBeVisible();
  await expect(page.getByTestId('gps-fix')).toHaveText('Location within 12 m');
  await page.getByTestId('capture-continue').click();

  await expect(page.getByTestId('wizard-step')).toHaveText('Step 3 of 4: Details');
  await page.getByLabel('Short title').fill(title);
  await page.getByLabel('What is the problem?').fill('Deep pothole in the left lane near the bus stop. Two-wheelers swerve around it.');
  await page.getByLabel('Landmark (optional)').fill('Near the bus stop');
  await page.getByLabel('About a finger deep').check();
  await page.getByLabel('An A4 sheet is in the photo').check();
  await expectNoHorizontalScroll(page);
  await shot('P11_wizard_3_details');
  await page.getByTestId('wizard-next').click();

  await expect(page.getByTestId('wizard-step')).toHaveText('Step 4 of 4: Review and send');
  await expect(page.getByRole('img', { name: 'Your photo' })).toBeVisible();
  await expect(page.locator('.leaflet-container')).toBeVisible();
  await expect(page.getByText('© OpenStreetMap contributors')).toBeVisible();
}

test('ui.citizen: empty list → wizard → CB number → list → detail; outside TDMC → OUTSIDE_BOUNDARY', async ({
  page,
  context,
}, testInfo) => {
  const phone = testInfo.project.name === 'phone';
  const shot = async (name: string) => {
    if (!phone) return;
    await page.evaluate(() => window.scrollTo(0, 0));
    const tall = await page.evaluate(() => document.documentElement.scrollHeight > window.innerHeight);
    const path = `../docs/screenshots/${name}.png`;
    await page.screenshot({ path, fullPage: true, ...(tall ? { style: FULL_PAGE_STYLE } : {}) });
  };
  await context.route('https://tile.openstreetmap.org/**', (route) => route.abort());
  await useFakeGps(context, INSIDE_TDMC);

  // 0. Log in as ui.citizen
  const citizen = uiCitizen();
  await page.goto('/login');
  await page.getByLabel('E-mail or mobile number').fill(citizen.email);
  await page.getByLabel('Password', { exact: true }).fill(citizen.password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL('/citizen');

  // 1. My complaints of the freshly seeded account: the empty state (phone runs first)
  await page.getByTestId('nav-citizen-complaints').click();
  await expect(page.getByRole('heading', { level: 1, name: 'My complaints' })).toBeVisible();
  if (phone) {
    await expect(page.getByText('You have not reported a problem yet.')).toBeVisible();
    await expect(page.getByRole('main').getByRole('link', { name: 'Report a problem' })).toBeVisible();
    await expectNoHorizontalScroll(page);
    await shot('P11_list_empty');
  }

  // 2. Wizard at the granted location inside TDMC → submit
  await wizardToReview(page, `Walkthrough pothole ${testInfo.project.name}`, shot);
  await expectNoHorizontalScroll(page);
  await shot('P11_wizard_4_review');
  await page.getByTestId('complaint-submit').click();
  const outcome = page.getByTestId('success-ref').or(page.getByRole('alert'));
  await expect(outcome.first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('success-ref'), 'submit inside TDMC must succeed').toHaveText(/^CB-\d{6,}$/);
  const publicRef = (await page.getByTestId('success-ref').textContent()) ?? '';
  await expect(page.getByText("You'll get e-mail/WhatsApp updates at every step.")).toBeVisible();
  await expect(page.getByText(/^Ward \d+$/)).toBeVisible();
  await expectNoHorizontalScroll(page);
  await shot('P11_wizard_5_success');
  testInfo.annotations.push({ type: 'submitted', description: publicRef });

  // 3. Detail of the new complaint: photo through ProtectedImage, timeline
  await page.getByTestId('success-view').click();
  await expect(page.getByRole('heading', { level: 1, name: `Walkthrough pothole ${testInfo.project.name}` })).toBeVisible();
  await expect(page.getByText(publicRef, { exact: true })).toBeVisible();
  await expect(page.locator('img[alt="Your photo"]')).toBeVisible();
  await expect(page.getByRole('list', { name: 'Progress' }).getByText('Received')).toBeVisible();
  await expectNoHorizontalScroll(page);
  await shot('P11_detail');

  // 4. The list now has it under "Open"
  await page.getByTestId('nav-citizen-complaints').click();
  await expect(page.getByRole('button', { name: 'Open' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByTestId('complaint-card').filter({ hasText: publicRef })).toBeVisible();
  await expect(page.locator('img[alt^="Photo of"]').first()).toBeVisible();
  await expectNoHorizontalScroll(page);
  await shot('P11_list');

  // 5. Outside TDMC: the server answers OUTSIDE_BOUNDARY → back to the photo step, typed text kept
  await useFakeGps(context, OUTSIDE_TDMC); // takes effect with the page load in wizardToReview
  await wizardToReview(page, 'Walkthrough outside test', async () => undefined);
  await page.getByTestId('complaint-submit').click();
  await expect(page.getByText('This location is outside Talegaon Dabhade Municipal Council.')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('Your title and description are kept.')).toBeVisible();
  await expect(page.getByTestId('wizard-step')).toHaveText('Step 2 of 4: Photo and location');
  await expectNoHorizontalScroll(page);
  await shot('P11_error_outside_boundary');
});
