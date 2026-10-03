// Pure rules of the in-page camera (docs/05_UI_SPEC.md §4 step 2, §7; docs/12_ERROR_HANDLING.md §6).

/** What CameraCapture hands back (05 §7). `capturedAt` is the location fix time (the API checks LOCATION_STALE). */
export interface CaptureResult {
  blob: Blob;
  lat: number;
  lon: number;
  accuracyM: number;
  capturedAt: string;
  /** DeviceOrientation `beta` at the shutter (camera depression = 90 − beta, docs/06 Tier B); null = not available. */
  pitchDeg: number | null;
  /** DeviceOrientation `gamma` at the shutter; null = not available. */
  rollDeg: number | null;
  method: 'IN_APP_CAMERA' | 'FILE_CAPTURE';
}

export const JPEG_QUALITY = 0.9;
export const MAX_ACCURACY_M = 150;
const GOOD_ACCURACY_M = 50;

export const CAMERA_CONSTRAINTS: MediaStreamConstraints = {
  video: { facingMode: 'environment', width: { ideal: 1920 } },
  audio: false,
};

export const FIX_OPTIONS: PositionOptions = { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 };
export const WATCH_OPTIONS: PositionOptions = { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 };

/** Why the in-page camera is not available → which explanation the fallback shows. */
export type CameraProblem = 'denied' | 'missing' | 'busy' | 'insecure' | 'unsupported';

export function cameraProblemOf(error: unknown): CameraProblem {
  const name = error instanceof DOMException || error instanceof Error ? error.name : '';
  switch (name) {
    case 'NotAllowedError':
    case 'PermissionDeniedError':
      return 'denied';
    case 'SecurityError':
      return window.isSecureContext ? 'denied' : 'insecure';
    case 'NotFoundError':
    case 'DevicesNotFoundError':
    case 'OverconstrainedError':
      return 'missing';
    case 'NotReadableError':
    case 'TrackStartError':
    case 'AbortError':
      return 'busy';
    default:
      return 'unsupported';
  }
}

/** No `getUserMedia` at all: plain http (not localhost) or an old browser. */
export function cameraUnavailable(): CameraProblem | null {
  if (typeof navigator.mediaDevices?.getUserMedia === 'function') return null;
  return window.isSecureContext ? 'unsupported' : 'insecure';
}

export type Tone = 'good' | 'warn' | 'bad' | 'none';

/** GPS chip colour: green ≤ 50 m, amber ≤ 150 m, red > 150 m (05 §4 step 2). */
export function accuracyTone(accuracyM: number): Tone {
  if (accuracyM <= GOOD_ACCURACY_M) return 'good';
  if (accuracyM <= MAX_ACCURACY_M) return 'warn';
  return 'bad';
}

export interface Orientation {
  beta: number;
  gamma: number;
}

export type TiltState = { tone: 'none' } | { tone: 'good' | 'warn'; downDeg: number; hint: 'good' | 'adjust' | 'level' };

/** Green when the camera points 45–70° below the horizon (90 − beta) and the roll |gamma| is under 5°. */
export function tiltState(orientation: Orientation | null): TiltState {
  if (orientation === null) return { tone: 'none' };
  const downDeg = Math.round(90 - orientation.beta);
  const level = Math.abs(orientation.gamma) < 5;
  const angled = downDeg >= 45 && downDeg <= 70;
  if (angled && level) return { tone: 'good', downDeg, hint: 'good' };
  return { tone: 'warn', downDeg, hint: angled ? 'level' : 'adjust' };
}

/** Accepted photo types (the server checks JPEG/PNG magic bytes, docs/12 FILE_TYPE_NOT_ALLOWED). */
export function isAllowedPhoto(file: Blob): boolean {
  return file.type === 'image/jpeg' || file.type === 'image/png';
}
