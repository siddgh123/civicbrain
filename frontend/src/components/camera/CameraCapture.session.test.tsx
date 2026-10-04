import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../lib/api';
import {
  installDeniedCamera,
  installGeolocation,
  installObjectUrls,
  jpegFile,
  removeBrowserFakes,
  TDMC_FIX,
} from '../../test/browserFakes';
import type { CaptureResult } from './capture';
import { CameraCapture } from './CameraCapture';

// docs/04 §5 + prompt P11: POST /citizen/capture-sessions happens right before the camera opens and the session id
// travels with the capture.

beforeEach(() => installObjectUrls());

afterEach(() => {
  removeBrowserFakes();
  vi.restoreAllMocks();
});

describe('CameraCapture with a capture session', () => {
  it('opens the session before the camera and returns its id with the capture', async () => {
    installGeolocation({ fix: TDMC_FIX });
    const order: string[] = [];
    const camera = installDeniedCamera();
    camera.getUserMedia.mockImplementation(() => {
      order.push('camera');
      return Promise.reject(new DOMException('Permission denied', 'NotAllowedError'));
    });
    const openSession = vi.fn(() => {
      order.push('session');
      return Promise.resolve('session-7');
    });
    const onCapture = vi.fn<(result: CaptureResult) => void>();
    const user = userEvent.setup();
    render(<CameraCapture onCapture={onCapture} openSession={openSession} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));
    await user.upload(await screen.findByTestId('capture-file'), jpegFile());
    await user.click(await screen.findByRole('button', { name: 'Use this photo' }));

    expect(order).toEqual(['session', 'camera']);
    expect(onCapture).toHaveBeenCalledTimes(1);
    expect(onCapture.mock.calls[0]?.[0]).toMatchObject({ captureSessionId: 'session-7', method: 'FILE_CAPTURE' });
  });

  it('a failed session request shows the error and does not open the camera', async () => {
    installGeolocation({ fix: TDMC_FIX });
    const camera = installDeniedCamera();
    const openSession = vi.fn(() =>
      Promise.reject(new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Network request failed' })),
    );
    const user = userEvent.setup();
    render(<CameraCapture onCapture={vi.fn()} openSession={openSession} />);

    await user.click(screen.getByRole('button', { name: 'Capture' }));

    expect(await screen.findByText('Cannot reach CivicBrain. Check your connection and try again.')).toBeInTheDocument();
    expect(camera.getUserMedia).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Capture' })).toBeEnabled();
  });
});
