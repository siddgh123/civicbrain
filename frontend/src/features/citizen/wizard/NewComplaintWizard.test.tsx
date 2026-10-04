import { screen, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../../../lib/api';
import {
  FIX_TIME,
  installDeniedCamera,
  installGeolocation,
  installObjectUrls,
  jpegFile,
  removeBrowserFakes,
  TDMC_FIX,
} from '../../../test/browserFakes';
import { problem, renderApp, signedIn } from '../../../test/renderApp';
import { server } from '../../../test/server';

// Requirement: FR-10 (wizard + in-app camera, no submit without photo + GPS), FR-12 (depth answer + A4 flag);
// docs/05 §4 steps 1-5, docs/04 §5, docs/12 §2 intake codes + §6 "never lose form input"; 09_7DAY §4 wizard test.
// The real CameraCapture runs through its file fallback (jsdom has no camera, like the headless browser).

const CATEGORIES = [
  { id: 1, name: 'Pothole', workTypeCode: 'ROAD', citizenSelectable: true, needsDepthAnswer: true },
  { id: 3, name: 'Garbage Accumulation', workTypeCode: 'GARBAGE', citizenSelectable: true, needsDepthAnswer: false },
  { id: 4, name: 'Waterlogging', workTypeCode: 'WATER', citizenSelectable: true, needsDepthAnswer: true },
  { id: 9, name: 'Internal only', workTypeCode: 'ROAD', citizenSelectable: false, needsDepthAnswer: false },
];

interface Calls {
  sessions: number;
  submits: number;
}

function mockIntake(submit: (request: Request) => Promise<Response> | Response): Calls {
  const calls: Calls = { sessions: 0, submits: 0 };
  server.use(
    http.get('/api/v1/public/categories', () => HttpResponse.json(CATEGORIES)),
    http.post('/api/v1/citizen/capture-sessions', () => {
      calls.sessions += 1;
      return HttpResponse.json(
        { captureSessionId: `session-${calls.sessions}`, expiresAt: '2026-10-04T09:10:00+05:30' },
        { status: 201 },
      );
    }),
    http.post('/api/v1/citizen/complaints', ({ request }) => {
      calls.submits += 1;
      return submit(request);
    }),
  );
  return calls;
}

const created = () =>
  HttpResponse.json({ complaintId: 41, publicRef: 'CB-000123', status: 'SUBMITTED', wardNumber: 7 }, { status: 201 });

function openWizard() {
  return renderApp('/citizen/new', { auth: signedIn('CITIZEN') });
}

async function chooseCategory(user: UserEvent, name: string) {
  await user.click(await screen.findByRole('button', { name }));
}

/** Step 2: Capture → (camera denied) file fallback → photo → "Use this photo". */
async function capturePhoto(user: UserEvent) {
  await user.click(await screen.findByRole('button', { name: 'Capture' }));
  await user.upload(await screen.findByTestId('capture-file'), jpegFile());
  await user.click(await screen.findByRole('button', { name: 'Use this photo' }));
}

async function fillDetails(user: UserEvent, title = 'Deep pothole near bus stop') {
  await user.type(await screen.findByLabelText('Short title'), title);
  await user.type(screen.getByLabelText('What is the problem?'), 'A deep pothole in the left lane, bikes swerve around it.');
}

beforeEach(() => {
  installObjectUrls();
  installDeniedCamera();
});

afterEach(() => {
  removeBrowserFakes();
  vi.restoreAllMocks();
});

describe('New complaint wizard', () => {
  it('blocks submit without photo or GPS: no way past step 2 and nothing is sent', async () => {
    installGeolocation({ deniedCode: 1 });
    const calls = mockIntake(created);
    const { user } = openWizard();

    expect(await screen.findByText('Step 1 of 4: Category')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Internal only' })).not.toBeInTheDocument();
    await chooseCategory(user, 'Pothole');
    expect(await screen.findByText('Step 2 of 4: Photo and location')).toBeInTheDocument();
    // no photo yet: neither Next nor Send exist
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Send report' })).not.toBeInTheDocument();

    // a photo but no location: "Use this photo" stays disabled
    await user.click(screen.getByRole('button', { name: 'Capture' }));
    await user.upload(await screen.findByTestId('capture-file'), jpegFile());
    const usePhoto = await screen.findByRole('button', { name: 'Use this photo' });
    expect(usePhoto).toBeDisabled();
    await user.click(usePhoto);

    expect(screen.getByText('Step 2 of 4: Photo and location')).toBeInTheDocument();
    expect(screen.getByText(/CivicBrain needs your location/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Send report' })).not.toBeInTheDocument();
    expect(calls.submits).toBe(0);
    // the capture session was opened right before the camera (04 §5), once
    expect(calls.sessions).toBe(1);
  });

  it('asks the depth question only for Pothole / Waterlogging (own labels) and requires it there', async () => {
    installGeolocation({ fix: TDMC_FIX });
    mockIntake(created);
    const { user } = openWizard();

    await chooseCategory(user, 'Pothole');
    expect(await screen.findByText('Optional: place an A4 sheet next to it, it helps to estimate the size.')).toBeInTheDocument();
    await capturePhoto(user);
    expect(await screen.findByText('Step 3 of 4: Details')).toBeInTheDocument();
    await fillDetails(user);
    const pothole = screen.getByRole('radiogroup', { name: 'How deep is the pothole?' });
    expect(within(pothole).getAllByRole('radio').map((r) => r.closest('label')?.textContent)).toEqual([
      'Shallower than a finger',
      'About a finger deep',
      'Deeper',
    ]);

    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Please choose one answer.')).toBeInTheDocument();
    expect(screen.getByText('Step 3 of 4: Details')).toBeInTheDocument();

    // Garbage: no depth question, no A4 tip; the photo and the typed text stay
    await user.click(screen.getByRole('button', { name: 'Back' }));
    expect(await screen.findByText('Photo and location are ready.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Back' }));
    await chooseCategory(user, 'Garbage Accumulation');
    expect(await screen.findByText('Photo and location are ready.')).toBeInTheDocument();
    expect(screen.queryByText(/place an A4 sheet/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByLabelText('Short title')).toHaveValue('Deep pothole near bus stop');
    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Step 4 of 4: Review and send')).toBeInTheDocument();

    // Waterlogging: ankle / knee labels, required again
    await user.click(screen.getByRole('button', { name: 'Back' }));
    await user.click(await screen.findByRole('button', { name: 'Back' }));
    await user.click(await screen.findByRole('button', { name: 'Back' }));
    await chooseCategory(user, 'Waterlogging');
    await user.click(await screen.findByRole('button', { name: 'Next' }));
    const water = await screen.findByRole('radiogroup', { name: 'How deep is the water?' });
    expect(within(water).getAllByRole('radio').map((r) => r.closest('label')?.textContent)).toEqual([
      'Below the ankle',
      'Below the knee',
      'Above the knee',
    ]);
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Please choose one answer.')).toBeInTheDocument();
    await user.click(within(water).getByLabelText('Below the knee'));
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(await screen.findByText('Step 4 of 4: Review and send')).toBeInTheDocument();
    expect(screen.getByText('Below the knee')).toBeInTheDocument();
  });

  it('sends the multipart request with the capture session and shows the CB number and ward', async () => {
    installGeolocation({ fix: TDMC_FIX });
    // Node's fetch cannot stream a jsdom FormData body, so the handler does not read it: the FormData the app builds
    // is read from the (call-through) spy instead. The real multipart upload is checked by the E2E walkthrough.
    const multipart = vi.spyOn(api, 'postMultipart');
    mockIntake(created);
    const { user, router } = openWizard();

    await chooseCategory(user, 'Pothole');
    await capturePhoto(user);
    await fillDetails(user, '  Deep pothole near bus stop  ');
    await user.click(screen.getByLabelText('About a finger deep'));
    await user.click(screen.getByLabelText('An A4 sheet is in the photo'));
    await user.click(screen.getByRole('button', { name: 'Next' }));

    expect(await screen.findByText('Step 4 of 4: Review and send')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Your photo' })).toBeInTheDocument();
    expect(screen.getByText('About a finger deep')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Send report' }));

    expect(await screen.findByTestId('success-ref')).toHaveTextContent('CB-000123');
    expect(screen.getByText('Ward 7')).toBeInTheDocument();
    expect(screen.getByText("You'll get e-mail/WhatsApp updates at every step.")).toBeInTheDocument();
    expect(multipart).toHaveBeenCalledTimes(1);
    const [path, , form] = multipart.mock.calls[0]!;
    expect(path).toBe('/citizen/complaints');
    const dataPart = form.get('data');
    const photo = form.get('photo');
    expect(dataPart).toBeInstanceOf(Blob);
    expect((dataPart as Blob).type).toBe('application/json');
    expect(JSON.parse(await (dataPart as Blob).text())).toEqual({
      categoryId: 1,
      title: 'Deep pothole near bus stop',
      description: 'A deep pothole in the left lane, bikes swerve around it.',
      latitude: TDMC_FIX.latitude,
      longitude: TDMC_FIX.longitude,
      locationAccuracyM: TDMC_FIX.accuracy,
      locationCapturedAt: FIX_TIME,
      captureSessionId: 'session-1',
      captureMethod: 'FILE_CAPTURE',
      a4InFrame: true,
      depthAnswer: 'FINGER',
    });
    expect(photo).toBeInstanceOf(File);
    expect((photo as File).type).toBe('image/jpeg');
    expect((photo as File).name).toBe('photo.jpg');

    await user.click(screen.getByRole('link', { name: 'View my complaint' }));
    expect(router.state.location.pathname).toBe('/citizen/complaints/41');
  });

  it('422 GPS_ACCURACY_TOO_LOW shows the open-sky message, asks for a new capture and keeps the typed text', async () => {
    installGeolocation({ fix: TDMC_FIX });
    const calls = mockIntake(() => problem(422, 'GPS_ACCURACY_TOO_LOW'));
    const { user } = openWizard();

    await chooseCategory(user, 'Garbage Accumulation');
    await capturePhoto(user);
    await fillDetails(user, 'Garbage heap at the corner');
    await user.type(screen.getByLabelText('Landmark (optional)'), 'Near Ganesh temple');
    await user.click(screen.getByRole('button', { name: 'Next' }));
    await user.click(await screen.findByRole('button', { name: 'Send report' }));

    expect(await screen.findByText('Move to open sky and retry.')).toBeInTheDocument();
    expect(screen.getByText('Your title and description are kept.')).toBeInTheDocument();
    expect(screen.getByText('Step 2 of 4: Photo and location')).toBeInTheDocument();
    expect(calls.submits).toBe(1);

    await capturePhoto(user);
    expect(await screen.findByLabelText('Short title')).toHaveValue('Garbage heap at the corner');
    expect(screen.getByLabelText('What is the problem?')).toHaveValue(
      'A deep pothole in the left lane, bikes swerve around it.',
    );
    expect(screen.getByLabelText('Landmark (optional)')).toHaveValue('Near Ganesh temple');
    // the new capture got a new single-use session
    expect(calls.sessions).toBe(2);
  });

  it('a server field error on the title goes back to the details step and shows it on the field', async () => {
    installGeolocation({ fix: TDMC_FIX });
    mockIntake(() =>
      problem(400, 'VALIDATION_FAILED', { fieldErrors: [{ field: 'title', code: 'SIZE', message: 'size must be between 5 and 120' }] }),
    );
    const { user } = openWizard();

    await chooseCategory(user, 'Garbage Accumulation');
    await capturePhoto(user);
    await fillDetails(user, 'Garbage heap');
    await user.click(screen.getByRole('button', { name: 'Next' }));
    await user.click(await screen.findByRole('button', { name: 'Send report' }));

    expect(await screen.findByText('Step 3 of 4: Details')).toBeInTheDocument();
    expect(screen.getByLabelText('Short title')).toHaveValue('Garbage heap');
    expect(screen.getByLabelText('Short title')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Use 5 to 120 characters.')).toBeInTheDocument();
  });
});
