import { vi } from 'vitest';

// jsdom has no camera, canvas encoder or geolocation: tests that drive CameraCapture install the browser APIs they
// need here and call `removeBrowserFakes()` in afterEach (after cleanup, so unmounting still finds them).

type PositionCallback = (position: GeolocationPosition) => void;
type ErrorCallback = (error: GeolocationPositionError) => void;

export interface FakeFix {
  latitude: number;
  longitude: number;
  accuracy: number;
}

/** Inside TDMC (CLAUDE.md "Browser checks" uses the same point for the walkthrough). */
export const TDMC_FIX: FakeFix = { latitude: 18.744, longitude: 73.676, accuracy: 12 };

export const FIX_TIME = '2026-10-04T03:30:00.000Z';

export function installGeolocation(mode: { fix: FakeFix } | { deniedCode: number }) {
  const answer = (ok: PositionCallback, fail?: ErrorCallback | null) => {
    if ('fix' in mode) {
      ok({ coords: { ...mode.fix }, timestamp: Date.parse(FIX_TIME) } as GeolocationPosition);
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

/** getUserMedia rejects (as in the headless browser): CameraCapture shows its file fallback. */
export function installDeniedCamera() {
  const mediaDevices = {
    getUserMedia: vi.fn(() => Promise.reject(new DOMException('Permission denied', 'NotAllowedError'))),
  };
  Object.defineProperty(navigator, 'mediaDevices', { value: mediaDevices, configurable: true });
  return mediaDevices;
}

export function installObjectUrls() {
  Object.defineProperty(URL, 'createObjectURL', { value: vi.fn(() => 'blob:preview'), configurable: true });
  Object.defineProperty(URL, 'revokeObjectURL', { value: vi.fn(), configurable: true });
}

export function removeBrowserFakes() {
  Reflect.deleteProperty(navigator, 'mediaDevices');
  Reflect.deleteProperty(navigator, 'geolocation');
}

export function jpegFile(name = 'photo.jpg'): File {
  return new File(['jpeg-bytes'], name, { type: 'image/jpeg' });
}
