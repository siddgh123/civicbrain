import { useEffect, useRef, useState, type RefObject } from 'react';
import { WATCH_OPTIONS, type Orientation } from './capture';

/** iOS 13+ asks for motion access; it must be requested inside the tap on "Capture" (05 §4 step 2). */
export async function requestOrientationPermission(): Promise<void> {
  const ctor: unknown = typeof DeviceOrientationEvent === 'undefined' ? undefined : DeviceOrientationEvent;
  if (typeof ctor !== 'function' || !('requestPermission' in ctor) || typeof ctor.requestPermission !== 'function') {
    return;
  }
  try {
    await (ctor.requestPermission as () => Promise<string>)();
  } catch {
    // Denied or not allowed here: the tilt indicator says "Angle not available", capture still works.
  }
}

/**
 * Live `beta`/`gamma` from `deviceorientation` (whole degrees, so the overlay re-renders only on a change). The ref
 * holds the newest value for the shutter.
 */
export function useDeviceOrientation(): { orientation: Orientation | null; latest: RefObject<Orientation | null> } {
  const [orientation, setOrientation] = useState<Orientation | null>(null);
  const latest = useRef<Orientation | null>(null);
  useEffect(() => {
    const onOrientation = (event: Event) => {
      const { beta, gamma } = event as DeviceOrientationEvent;
      if (typeof beta !== 'number' || typeof gamma !== 'number') return;
      const next = { beta: Math.round(beta * 10) / 10, gamma: Math.round(gamma * 10) / 10 };
      latest.current = next;
      setOrientation((prev) =>
        prev !== null && Math.round(prev.beta) === Math.round(next.beta) && Math.round(prev.gamma) === Math.round(next.gamma)
          ? prev
          : next,
      );
    };
    window.addEventListener('deviceorientation', onOrientation);
    return () => window.removeEventListener('deviceorientation', onOrientation);
  }, []);
  return { orientation, latest };
}

export type GpsProblem = 'denied' | 'unavailable' | 'unsupported';

export type GpsReading = { kind: 'ok'; accuracyM: number } | { kind: 'error'; problem: GpsProblem };

export function gpsProblemOf(error: GeolocationPositionError): GpsProblem {
  return error.code === 1 ? 'denied' : 'unavailable'; // 1 = PERMISSION_DENIED; 2/3 = unavailable / timeout
}

/** `watchPosition` while `active` (live accuracy chip). null = still waiting for the first reading. */
export function useGpsWatch(active: boolean): GpsReading | null {
  const [reading, setReading] = useState<GpsReading | null>(null);
  useEffect(() => {
    if (!active) return undefined;
    if (!('geolocation' in navigator)) {
      queueMicrotask(() => setReading({ kind: 'error', problem: 'unsupported' }));
      return undefined;
    }
    const geolocation = navigator.geolocation;
    const id = geolocation.watchPosition(
      (position) => setReading({ kind: 'ok', accuracyM: position.coords.accuracy }),
      (error) => setReading({ kind: 'error', problem: gpsProblemOf(error) }),
      WATCH_OPTIONS,
    );
    return () => geolocation.clearWatch(id);
  }, [active]);
  return reading;
}
