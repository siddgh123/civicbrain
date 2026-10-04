import { readFileSync } from 'node:fs';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

// P07 Verify 2 on the E2E stack (start-all.ps1 -E2E): register → OTP from Mailpit → verify → login → citizen home →
// logout → login as ui.citizen → reload keeps the session (refresh cookie) → /citizen/new camera step → fallback.
// Run: npx playwright test --config playwright.walkthrough.config.ts walkthrough/P07
// The ui.citizen password is read from the git-ignored accounts file at run time and never printed or screenshotted.

const MAILPIT = 'http://localhost:8025';
const ACCOUNTS_FILE = new URL('../../tests/e2e-ui-accounts.local.json', import.meta.url);

test.use({
  geolocation: { latitude: 18.744, longitude: 73.676, accuracy: 12 },
  permissions: ['geolocation'], // no camera permission and no camera: the fallback must appear
});

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

function randomChars(length: number, alphabet: string): string {
  return Array.from({ length }, () => alphabet[Math.floor(Math.random() * alphabet.length)]).join('');
}

/** The 6-digit code of the newest verification mail to `to` (Mailpit API; the code is never logged). */
async function readOtp(request: APIRequestContext, to: string): Promise<string> {
  let code = '';
  await expect
    .poll(
      async () => {
        const search = await request.get(`${MAILPIT}/api/v1/search`, { params: { query: `to:"${to}"`, limit: 20 } });
        const list = (await search.json()) as { messages?: { ID: string; Subject: string }[] };
        for (const message of list.messages ?? []) {
          if (!message.Subject.includes('verification code')) continue;
          const full = (await (await request.get(`${MAILPIT}/api/v1/message/${message.ID}`)).json()) as { Text?: string };
          const match = /verification code is (\d{6})/.exec(full.Text ?? '');
          if (match?.[1] !== undefined) {
            code = match[1];
            return true;
          }
        }
        return false;
      },
      { timeout: 30_000, intervals: [1000] },
    )
    .toBe(true);
  return code;
}

async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

async function logIn(page: Page, identifier: string, password: string) {
  const field = page.getByLabel('E-mail or mobile number');
  if ((await field.inputValue()) !== identifier) await field.fill(identifier);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Log in' }).click();
}

test('register → OTP → login → logout → ui.citizen → camera fallback', async ({ page, request }, testInfo) => {
  const shoot = testInfo.project.name === 'phone';
  const email = `p07-${randomChars(4, 'abcdefghijkmnpqrstuvwxyz23456789')}@smoke.local`;
  const phone = `9${randomChars(9, '0123456789')}`;
  // must not contain the name or the e-mail (password policy, docs/07 §1)
  const password = `river lantern ${randomChars(8, 'abcdefghijkmnpqrstuvwxyz')} mango`;

  // 1. Register (privacy notice from the backend, consents)
  await page.goto('/register');
  await expect(page.getByRole('heading', { level: 1, name: 'Create an account' })).toBeVisible();
  await expect(page.getByTestId('privacy-notice')).not.toBeEmpty();
  await page.getByLabel('Full name').fill('P07 Walkthrough');
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Mobile number').fill(phone);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('I have read the privacy notice and I accept it.').check();
  await page.getByLabel('Send me WhatsApp updates about my complaints').check();
  await expect(page.getByTestId('password-strength')).toContainText('Strong');
  await expectNoHorizontalScroll(page);
  if (shoot) await page.screenshot({ path: '../docs/screenshots/P07_register.png', fullPage: true });
  await page.getByRole('button', { name: 'Create account' }).click();

  // 2. OTP from Mailpit (screenshot before the code is typed). Register sends the mail synchronously; the first call
  // after a backend start can take several seconds.
  await expect(page.getByRole('heading', { level: 1, name: 'Enter the code' })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(`We sent a 6-digit code to ${email}`)).toBeVisible();
  await expect(page.getByTestId('otp-resend')).toBeDisabled();
  await expectNoHorizontalScroll(page);
  if (shoot) await page.screenshot({ path: '../docs/screenshots/P07_otp.png', fullPage: true });
  const code = await readOtp(request, email);
  await page.getByLabel('Digit 1 of 6').fill(code); // like the phone's one-time-code autofill
  await expect(page.getByLabel('Digit 6 of 6')).not.toHaveValue('');
  await page.getByRole('button', { name: 'Verify' }).click();

  // 3. Login (e-mail filled in) → citizen home
  await expect(page.getByText('Your e-mail address is verified. Please log in.')).toBeVisible();
  await expect(page.getByLabel('E-mail or mobile number')).toHaveValue(email);
  await logIn(page, email, password);
  await expect(page).toHaveURL('/citizen');
  await expect(page.getByRole('heading', { level: 1, name: 'Hello, P07 Walkthrough' })).toBeVisible();
  await expect(page.getByTestId('home-report')).toBeVisible();
  await expectNoHorizontalScroll(page);
  if (shoot) await page.screenshot({ path: '../docs/screenshots/P07_citizen_home.png', fullPage: true });

  // 4. Logout clears the session: the portal asks for login again, also after a reload
  await page.getByTestId('logout').click();
  await expect(page).toHaveURL('/');
  await page.goto('/citizen');
  await expect(page).toHaveURL('/login?returnTo=%2Fcitizen');

  // 5. ui.citizen; a reload restores the session through the __Host-cb_rt refresh cookie (silent refresh)
  const citizen = uiCitizen();
  await logIn(page, citizen.email, citizen.password);
  await expect(page).toHaveURL('/citizen');
  await expect(page.getByRole('heading', { level: 1, name: 'Hello, UI Citizen' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { level: 1, name: 'Hello, UI Citizen' })).toBeVisible();

  // 6. /citizen/new → (P11 wizard: category first) Pothole → Capture → no camera in the headless browser →
  // explanation + file fallback
  await page.getByTestId('home-report').click();
  await expect(page).toHaveURL('/citizen/new');
  await page.getByRole('button', { name: 'Pothole' }).click();
  await page.getByTestId('capture-start').click();
  await expect(page.getByRole('heading', { name: 'The camera could not be opened' })).toBeVisible();
  const fileInput = page.getByTestId('capture-file');
  await expect(fileInput).toHaveAttribute('accept', 'image/*');
  await expect(fileInput).toHaveAttribute('capture', 'environment');
  await expect(page.getByText('Take a photo with the phone camera')).toBeVisible();
  await expectNoHorizontalScroll(page);
  if (shoot) await page.screenshot({ path: '../docs/screenshots/P07_camera_fallback.png', fullPage: true });
});
