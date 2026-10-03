import { act, cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { CaptureResult } from './capture';
import { CameraCapture } from './CameraCapture';

// jsdom has no camera, canvas encoder or geolocation: each test installs the browser APIs it needs.

type PositionCallback = (position: GeolocationPosition) => void;
type ErrorCallback = (error: GeolocationPositionError) => void;

const TDMC_FIX = { latitude: 18.744, longitude: 73.676, accuracy: 12 };

function installGeolocation(mode: { fix: typeof TDMC_FIX } | { deniedCode: number }) {
  const answer = (ok: PositionCallback, fail?: ErrorCallback | null) => {
    if ('fix' in mode) {
      ok({ coords: { ...mode.fix }, timestamp: Date.parse('2026-10-03T08:00:00Z') } as GeolocationPosition);
    } else {
      fail?.({ code: mode.deniedCode, message: 'denied' } as GeolocationPositionError);
    }
  };
  const geolocation = {
    getCurrentPosition: vi.fn((ok: PositionCallback, fail?: ErrorCallback | null) => answer(ok, fail)),
    watchPosition: vi.fn((ok: PositionCallback, fail?: ErrorCallback | null) => {
      answer(ok, fail);
      return 1;
    }),
    clearWatch: vi.fn(),
  };
  Object.defineProperty(navigator, 'geolocation', { value: geolocation, configurable: true });
  return geolocation;
}

function installCamera(getUserMedia: () => Promise<MediaStream>) {
  const mediaDevices = { getUserMedia: vi.fn(getUserMedia) };
  Object.defineProperty(navigator, 'mediaDevices', { value: mediaDevices, configurable: true });
  return mediaDevices;
}

function fakeStream() {
  const track = { stop: vi.fn() };
  return { stream: { getTracks: () => [track] } as unknown as MediaStream, track };
}

beforeEach(() => {
  Object.defineProperty(URL, 'createObjectURL', { value: vi.fn(() => 'blob:preview'), configurable: true });
  Object.defineProperty(URL, 'revokeObjectURL', { value: vi.fn(), configurable: true });
});

afterEach(() => {
  cleanup(); // unmount while the fake browser APIs still exist
  vi.restoreAllMocks();
  Reflect.deleteProperty(navigator, 'mediaDevices');
  Reflect.deleteProperty(navigator, 'geolocation');
  Reflect.deleteProperty(window, 'isSecureContext');
});

describe('CameraCapture', () => {
  it('shows the explanation and the capture="environment" file fallback when getUserMedia rejects with NotAllowedError', async () => {
    installGeolocation({ fix: TDMC_FIX });
    const camera = installCamera(() => Promise.reject(new DOMException('Permission denied', 'NotAllowedError')));
    const user = userEvent.setup();
    render(<CameraCapture onCapture={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));

    expect(await screen.findByRole('heading', { name: 'The camera could not be opened' })).toBeInTheDocument();
    expect(screen.getByText(/Camera access was blocked/)).toBeInTheDocument();
    expect(camera.getUserMedia).toHaveBeenCalledWith({
      video: { facingMode: 'environment', width: { ideal: 1920 } },
      audio: false,
    });
    const fileInput = screen.getByTestId('capture-file');
    expect(fileInput).toHaveAttribute('type', 'file');
    expect(fileInput).toHaveAttribute('accept', 'image/*');
    expect(fileInput).toHaveAttribute('capture', 'environment');
    // no gallery picker: the only file input is the camera-capture one
    expect(document.querySelectorAll('input[type="file"]')).toHaveLength(1);
  });

  it('location denied blocks "Use this photo" and explains how to enable it', async () => {
    installGeolocation({ deniedCode: 1 });
    installCamera(() => Promise.reject(new DOMException('Permission denied', 'NotAllowedError')));
    const onCapture = vi.fn();
    const user = userEvent.setup();
    render(<CameraCapture onCapture={onCapture} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));
    await user.upload(
      await screen.findByTestId('capture-file'),
      new File(['jpeg-bytes'], 'photo.jpg', { type: 'image/jpeg' }),
    );

    expect(await screen.findByRole('img', { name: 'Photo preview' })).toBeInTheDocument();
    const continueButton = screen.getByRole('button', { name: 'Use this photo' });
    expect(continueButton).toBeDisabled();
    expect(screen.getByText(/CivicBrain needs your location/)).toBeInTheDocument();
    await user.click(continueButton);
    expect(onCapture).not.toHaveBeenCalled();
  });

  it('a fix worse than 150 m also blocks "Use this photo" ("Move to open sky")', async () => {
    installGeolocation({ fix: { ...TDMC_FIX, accuracy: 240 } });
    installCamera(() => Promise.reject(new DOMException('No camera', 'NotFoundError')));
    const user = userEvent.setup();
    render(<CameraCapture onCapture={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));
    expect(await screen.findByText(/No camera was found/)).toBeInTheDocument();
    await user.upload(screen.getByTestId('capture-file'), new File(['png'], 'p.png', { type: 'image/png' }));

    expect(await screen.findByText(/Move to open sky and retry. Location within 240 m/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Use this photo' })).toBeDisabled();
  });

  it('in-page camera: shutter → JPEG 0.9 + fresh fix + beta/gamma; tracks stop; result has method IN_APP_CAMERA', async () => {
    const geolocation = installGeolocation({ fix: TDMC_FIX });
    const { stream, track } = fakeStream();
    installCamera(() => Promise.resolve(stream));
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined);
    vi.spyOn(HTMLVideoElement.prototype, 'videoWidth', 'get').mockReturnValue(1920);
    vi.spyOn(HTMLVideoElement.prototype, 'videoHeight', 'get').mockReturnValue(1440);
    const drawImage = vi.fn();
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      drawImage,
    } as unknown as CanvasRenderingContext2D);
    const toBlob = vi
      .spyOn(HTMLCanvasElement.prototype, 'toBlob')
      .mockImplementation((callback: BlobCallback) => callback(new Blob(['jpeg'], { type: 'image/jpeg' })));
    const onCapture = vi.fn<(result: CaptureResult) => void>();
    const user = userEvent.setup();
    render(<CameraCapture onCapture={onCapture} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));
    expect(await screen.findByTestId('capture-video')).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(Object.assign(new Event('deviceorientation'), { alpha: 0, beta: 30, gamma: 2 }));
    });
    expect(screen.getByTestId('tilt-indicator')).toHaveTextContent('Angle good · 60°');
    expect(screen.getByTestId('gps-chip')).toHaveTextContent('Location within 12 m');
    expect(screen.getByTestId('gps-chip')).toHaveAttribute('data-tone', 'good');

    await user.click(screen.getByRole('button', { name: 'Take photo' }));

    expect(await screen.findByRole('img', { name: 'Photo preview' })).toHaveAttribute('src', 'blob:preview');
    expect(toBlob).toHaveBeenCalledWith(expect.any(Function), 'image/jpeg', 0.9);
    expect(drawImage).toHaveBeenCalled();
    expect(track.stop).toHaveBeenCalled();
    expect(geolocation.getCurrentPosition).toHaveBeenCalledWith(expect.any(Function), expect.any(Function), {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 20000,
    });
    await user.click(screen.getByRole('button', { name: 'Use this photo' }));

    expect(onCapture).toHaveBeenCalledTimes(1);
    const result = onCapture.mock.calls[0]?.[0];
    expect(result).toMatchObject({
      lat: 18.744,
      lon: 73.676,
      accuracyM: 12,
      capturedAt: '2026-10-03T08:00:00.000Z',
      pitchDeg: 30,
      rollDeg: 2,
      method: 'IN_APP_CAMERA',
    });
    expect(result?.blob.type).toBe('image/jpeg');
  });

  it('stops the camera tracks on unmount', async () => {
    installGeolocation({ fix: TDMC_FIX });
    const { stream, track } = fakeStream();
    installCamera(() => Promise.resolve(stream));
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined);
    const user = userEvent.setup();
    const { unmount } = render(<CameraCapture onCapture={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));
    expect(await screen.findByTestId('capture-video')).toBeInTheDocument();
    expect(track.stop).not.toHaveBeenCalled();

    unmount();

    expect(track.stop).toHaveBeenCalledTimes(1);
  });

  it('without getUserMedia on plain http the fallback explains the secure-address rule', async () => {
    installGeolocation({ fix: TDMC_FIX });
    Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true });
    const user = userEvent.setup();
    render(<CameraCapture onCapture={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));

    expect(await screen.findByText(/only works on a secure \(https\) address/)).toBeInTheDocument();
    expect(screen.getByTestId('capture-file')).toBeInTheDocument();
  });
});
