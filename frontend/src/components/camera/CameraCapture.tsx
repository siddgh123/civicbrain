import { useCallback, useEffect, useRef, useState, type ChangeEvent, type ReactNode, type RefObject } from 'react';
import { useTranslation } from 'react-i18next';
import { primaryButtonClass, secondaryButtonClass } from '../form/fields';
import { AlertIcon, CameraIcon, CheckIcon, MapPinIcon, RotateIcon } from '../icons/icons';
import {
  accuracyTone,
  CAMERA_CONSTRAINTS,
  cameraProblemOf,
  cameraUnavailable,
  FIX_OPTIONS,
  isAllowedPhoto,
  JPEG_QUALITY,
  MAX_ACCURACY_M,
  tiltState,
  type CameraProblem,
  type CaptureResult,
  type Tone,
} from './capture';
import { gpsProblemOf, requestOrientationPermission, useDeviceOrientation, useGpsWatch, type GpsProblem } from './sensors';

interface Photo {
  blob: Blob;
  url: string;
  method: CaptureResult['method'];
  pitchDeg: number | null;
  rollDeg: number | null;
}

type Phase =
  | { name: 'idle' }
  | { name: 'starting' }
  | { name: 'live' }
  | { name: 'fallback'; problem: CameraProblem }
  | { name: 'preview'; photo: Photo; problem: CameraProblem | null };

type Fix =
  | { status: 'pending' }
  | { status: 'ok'; lat: number; lon: number; accuracyM: number; at: string }
  | { status: 'error'; problem: GpsProblem };

interface CameraCaptureProps {
  /** "Use this photo": the photo with a location of 150 m or better. */
  onCapture: (result: CaptureResult) => void;
  /** Pothole / Waterlogging: "Optional: place an A4 sheet next to it". */
  showA4Tip?: boolean;
}

function stopTracks(stream: RefObject<MediaStream | null>): void {
  stream.current?.getTracks().forEach((track) => track.stop());
  stream.current = null;
}

function grabFrame(video: HTMLVideoElement): Promise<Blob | null> {
  const width = video.videoWidth;
  const height = video.videoHeight;
  if (width === 0 || height === 0) return Promise.resolve(null);
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  if (context === null) return Promise.resolve(null);
  context.drawImage(video, 0, 0, width, height);
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY));
}

const TONE_CLASSES: Record<Tone, string> = {
  good: 'bg-status-success-bg text-status-success-fg',
  warn: 'bg-status-warning-bg text-status-warning-fg',
  bad: 'bg-status-danger-bg text-status-danger-fg',
  none: 'bg-status-neutral-bg text-status-neutral-fg',
};

function Chip({ tone, icon, children, testId }: { tone: Tone; icon: ReactNode; children: ReactNode; testId?: string }) {
  return (
    <span
      data-testid={testId}
      data-tone={tone}
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold shadow-sm ${TONE_CLASSES[tone]}`}
    >
      {icon}
      {children}
    </span>
  );
}

/**
 * docs/05_UI_SPEC.md §4 step 2 + §7: in-page camera (rear, ~1920 px) with guide frame, live tilt indicator and GPS
 * accuracy chip; shutter → JPEG 0.9 + a fresh high-accuracy fix + beta/gamma; preview with Retake; no gallery.
 * Camera unavailable → explanation + `<input type="file" accept="image/*" capture="environment">` (FILE_CAPTURE).
 * Location denied or worse than 150 m → explanation, "Use this photo" stays disabled. Camera tracks stop on capture
 * and on unmount.
 */
export function CameraCapture({ onCapture, showA4Tip = false }: CameraCaptureProps) {
  const { t } = useTranslation();
  const [phase, setPhase] = useState<Phase>({ name: 'idle' });
  const [fix, setFix] = useState<Fix>({ status: 'pending' });
  const [failure, setFailure] = useState<string | null>(null);
  const [sensorsOn, setSensorsOn] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const fixRequest = useRef(0);
  const { orientation, latest } = useDeviceOrientation();
  const watch = useGpsWatch(sensorsOn && (phase.name === 'live' || phase.name === 'fallback'));

  useEffect(() => () => stopTracks(stream), []);

  const previewUrl = phase.name === 'preview' ? phase.photo.url : null;
  useEffect(() => {
    if (previewUrl === null) return undefined;
    return () => URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  useEffect(() => {
    const video = videoRef.current;
    if (phase.name !== 'live' || video === null || stream.current === null) return;
    video.srcObject = stream.current;
    void Promise.resolve(video.play()).catch(() => undefined);
  }, [phase.name]);

  const locate = useCallback(() => {
    const request = ++fixRequest.current;
    setFix({ status: 'pending' });
    if (!('geolocation' in navigator)) {
      setFix({ status: 'error', problem: 'unsupported' });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (request !== fixRequest.current) return;
        setFix({
          status: 'ok',
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          accuracyM: position.coords.accuracy,
          at: new Date(position.timestamp).toISOString(),
        });
      },
      (error) => {
        if (request === fixRequest.current) setFix({ status: 'error', problem: gpsProblemOf(error) });
      },
      FIX_OPTIONS,
    );
  }, []);

  const startCamera = useCallback(async () => {
    setFailure(null);
    const unavailable = cameraUnavailable();
    if (unavailable !== null) {
      setPhase({ name: 'fallback', problem: unavailable });
      return;
    }
    setPhase({ name: 'starting' });
    try {
      stopTracks(stream);
      stream.current = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS);
      setPhase({ name: 'live' });
    } catch (error) {
      setPhase({ name: 'fallback', problem: cameraProblemOf(error) });
    }
  }, []);

  const onStart = async () => {
    await requestOrientationPermission(); // iOS: must happen inside this tap
    setSensorsOn(true);
    await startCamera();
  };

  const showPreview = (blob: Blob, method: CaptureResult['method'], problem: CameraProblem | null) => {
    const reading = latest.current;
    setPhase({
      name: 'preview',
      problem,
      photo: {
        blob,
        url: URL.createObjectURL(blob),
        method,
        pitchDeg: reading?.beta ?? null,
        rollDeg: reading?.gamma ?? null,
      },
    });
    locate();
  };

  const onShutter = async () => {
    const video = videoRef.current;
    const blob = video === null ? null : await grabFrame(video);
    if (blob === null || blob.type !== 'image/jpeg') {
      setFailure(t('camera.captureFailed'));
      return;
    }
    stopTracks(stream);
    showPreview(blob, 'IN_APP_CAMERA', null);
  };

  const onFile = (problem: CameraProblem) => (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ''; // the same photo can be chosen again after Retake
    if (file === undefined) return;
    if (!isAllowedPhoto(file)) {
      setFailure(t('camera.wrongFileType'));
      return;
    }
    setFailure(null);
    showPreview(file, 'FILE_CAPTURE', problem);
  };

  const onRetake = () => {
    if (phase.name !== 'preview') return;
    fixRequest.current += 1;
    if (phase.problem !== null) setPhase({ name: 'fallback', problem: phase.problem });
    else void startCamera();
  };

  const canContinue = phase.name === 'preview' && fix.status === 'ok' && fix.accuracyM <= MAX_ACCURACY_M;
  const onContinue = () => {
    if (phase.name !== 'preview' || fix.status !== 'ok' || fix.accuracyM > MAX_ACCURACY_M) return;
    const { photo } = phase;
    onCapture({
      blob: photo.blob,
      lat: fix.lat,
      lon: fix.lon,
      accuracyM: fix.accuracyM,
      capturedAt: fix.at,
      pitchDeg: photo.pitchDeg,
      rollDeg: photo.rollDeg,
      method: photo.method,
    });
  };

  const tilt = tiltState(orientation);
  const tiltText =
    tilt.tone === 'none'
      ? t('camera.tiltUnknown')
      : `${t(tilt.hint === 'good' ? 'camera.tiltGood' : tilt.hint === 'level' ? 'camera.tiltLevel' : 'camera.tiltAdjust')} · ${tilt.downDeg}°`;

  const a4Tip = showA4Tip && <p className="text-sm text-slate-700">{t('camera.a4Tip')}</p>;
  const failureAlert = failure && (
    <p role="alert" className="rounded-lg border border-status-danger-border bg-status-danger-bg px-4 py-3 font-medium text-status-danger-fg">
      {failure}
    </p>
  );

  return (
    <div className="flex flex-col gap-4" data-testid="camera-capture">
      {phase.name === 'idle' && (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-8 text-center">
          <span className="grid size-14 place-items-center rounded-2xl bg-brand-50 text-brand-700">
            <CameraIcon className="size-8" />
          </span>
          <p className="text-slate-700">{t('camera.intro')}</p>
          {a4Tip}
          <button type="button" onClick={() => void onStart()} data-testid="capture-start" className={primaryButtonClass}>
            <CameraIcon className="size-5" />
            {t('camera.start')}
          </button>
        </div>
      )}

      {phase.name === 'starting' && (
        <div
          role="status"
          className="grid aspect-[3/4] max-h-[70dvh] w-full place-items-center rounded-2xl bg-slate-900 text-white motion-safe:animate-pulse"
        >
          {t('camera.starting')}
        </div>
      )}

      {phase.name === 'live' && (
        <>
          <div className="relative mx-auto aspect-[3/4] max-h-[70dvh] w-full overflow-hidden rounded-2xl bg-black">
            <video ref={videoRef} playsInline muted autoPlay className="size-full object-cover" data-testid="capture-video" />
            <div aria-hidden="true" className="pointer-events-none absolute inset-[14%] rounded-xl border-2 border-dashed border-white/90" />
            <p className="pointer-events-none absolute inset-x-0 bottom-3 text-center text-sm font-medium text-white drop-shadow">
              {t('camera.guide')}
            </p>
            <div className="absolute inset-x-2 top-2 flex flex-wrap gap-2">
              <Chip tone={tilt.tone === 'none' ? 'none' : tilt.tone} icon={<RotateIcon className="size-4" />} testId="tilt-indicator">
                {tiltText}
              </Chip>
              <GpsChip watch={watch} />
            </div>
          </div>
          {a4Tip}
          {watch?.kind === 'error' && <LocationProblem problem={watch.problem} />}
          {failureAlert}
          <button
            type="button"
            onClick={() => void onShutter()}
            data-testid="capture-shutter"
            aria-label={t('camera.shutter')}
            className="mx-auto grid size-20 place-items-center rounded-full border-4 border-brand-700 bg-white shadow-md hover:bg-brand-50"
          >
            <CameraIcon className="size-8 text-brand-800" />
          </button>
        </>
      )}

      {phase.name === 'fallback' && (
        <div className="flex flex-col gap-4 rounded-2xl border border-status-warning-border bg-status-warning-bg p-5" data-testid="capture-fallback">
          <div className="flex items-start gap-3 text-status-warning-fg">
            <AlertIcon className="mt-0.5 size-6 shrink-0" />
            <div className="flex flex-col gap-1">
              <h2 className="font-bold">{t('camera.fallbackTitle')}</h2>
              <p>{t(FALLBACK_TEXT[phase.problem])}</p>
            </div>
          </div>
          {a4Tip}
          <label className={`${primaryButtonClass} cursor-pointer focus-within:outline-3 focus-within:outline-offset-2 focus-within:outline-brand-600`}>
            <CameraIcon className="size-5" />
            {t('camera.fallbackButton')}
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={onFile(phase.problem)}
              data-testid="capture-file"
              className="sr-only"
            />
          </label>
          {(phase.problem === 'denied' || phase.problem === 'busy') && (
            <button type="button" onClick={() => void startCamera()} className={secondaryButtonClass}>
              {t('camera.tryCameraAgain')}
            </button>
          )}
          {watch?.kind === 'error' && <LocationProblem problem={watch.problem} />}
          {failureAlert}
        </div>
      )}

      {phase.name === 'preview' && (
        <>
          <img
            src={phase.photo.url}
            alt={t('camera.preview')}
            data-testid="capture-preview"
            className="mx-auto max-h-[60dvh] w-full rounded-2xl bg-slate-200 object-contain"
          />
          <FixStatus fix={fix} onRetry={locate} />
          <div className="grid grid-cols-2 gap-3">
            <button type="button" onClick={onRetake} data-testid="capture-retake" className={secondaryButtonClass}>
              <RotateIcon className="size-5" />
              {t('camera.retake')}
            </button>
            <button
              type="button"
              onClick={onContinue}
              disabled={!canContinue}
              data-testid="capture-continue"
              className={primaryButtonClass}
            >
              <CheckIcon className="size-5" />
              {t('camera.continue')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

const FALLBACK_TEXT = {
  denied: 'camera.cameraDenied',
  missing: 'camera.cameraMissing',
  busy: 'camera.cameraBusy',
  insecure: 'camera.cameraInsecure',
  unsupported: 'camera.cameraUnsupported',
} as const satisfies Record<CameraProblem, string>;

function GpsChip({ watch }: { watch: ReturnType<typeof useGpsWatch> }) {
  const { t } = useTranslation();
  const icon = <MapPinIcon className="size-4" />;
  if (watch === null) return <Chip tone="none" icon={icon} testId="gps-chip">{t('camera.gpsWaiting')}</Chip>;
  if (watch.kind === 'error') return <Chip tone="bad" icon={icon} testId="gps-chip">{t('camera.gpsDeniedTitle')}</Chip>;
  const meters = Math.round(watch.accuracyM);
  return (
    <Chip tone={accuracyTone(watch.accuracyM)} icon={icon} testId="gps-chip">
      {t('camera.gpsAccuracy', { meters })}
    </Chip>
  );
}

function LocationProblem({ problem, onRetry }: { problem: GpsProblem; onRetry?: () => void }) {
  const { t } = useTranslation();
  const text = { denied: 'camera.gpsDeniedText', unavailable: 'camera.gpsUnavailable', unsupported: 'camera.gpsUnsupported' } as const;
  return (
    <div role="alert" className="flex flex-col gap-3 rounded-xl border border-status-danger-border bg-status-danger-bg p-4 text-status-danger-fg">
      <div className="flex items-start gap-2">
        <MapPinIcon className="mt-0.5 size-5 shrink-0" />
        <div className="flex flex-col gap-1">
          <p className="font-bold">{t('camera.gpsDeniedTitle')}</p>
          <p>{t(text[problem])}</p>
        </div>
      </div>
      {onRetry && problem !== 'unsupported' && (
        <button type="button" onClick={onRetry} data-testid="gps-retry" className={secondaryButtonClass}>
          {t('camera.gpsRetry')}
        </button>
      )}
    </div>
  );
}

function FixStatus({ fix, onRetry }: { fix: Fix; onRetry: () => void }) {
  const { t } = useTranslation();
  if (fix.status === 'pending') {
    return (
      <p role="status" className="flex items-center gap-2 text-slate-700">
        <MapPinIcon className="size-5 text-slate-500" />
        {t('camera.gpsWaiting')}
      </p>
    );
  }
  if (fix.status === 'error') return <LocationProblem problem={fix.problem} onRetry={onRetry} />;
  const meters = Math.round(fix.accuracyM);
  if (fix.accuracyM > MAX_ACCURACY_M) {
    return (
      <div role="alert" className="flex flex-col gap-3 rounded-xl border border-status-danger-border bg-status-danger-bg p-4 text-status-danger-fg">
        <p className="font-semibold">{t('camera.gpsPoor', { meters })}</p>
        <button type="button" onClick={onRetry} data-testid="gps-retry" className={secondaryButtonClass}>
          {t('camera.gpsRetry')}
        </button>
      </div>
    );
  }
  return (
    <div>
      <Chip tone={accuracyTone(fix.accuracyM)} icon={<MapPinIcon className="size-4" />} testId="gps-fix">
        {t('camera.gpsAccuracy', { meters })}
      </Chip>
    </div>
  );
}
