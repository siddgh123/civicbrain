import { render, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAccessToken } from '../auth/tokenStore';
import { server } from '../test/server';
import { ProtectedImage } from './ProtectedImage';

beforeEach(() => {
  Object.defineProperty(URL, 'createObjectURL', { value: vi.fn(() => 'blob:photo-5'), configurable: true });
  Object.defineProperty(URL, 'revokeObjectURL', { value: vi.fn(), configurable: true });
});

afterEach(() => vi.restoreAllMocks());

describe('ProtectedImage', () => {
  it('fetches the photo with the bearer token, shows a blob URL and revokes it on unmount', async () => {
    let authorization: string | null = null;
    server.use(
      http.get('/api/v1/files/5', ({ request }) => {
        authorization = request.headers.get('authorization');
        return new HttpResponse(new Blob([new Uint8Array([0xff, 0xd8, 0xff])], { type: 'image/jpeg' }), {
          headers: { 'Content-Type': 'image/jpeg' },
        });
      }),
    );
    setAccessToken('photo-token');
    const { unmount } = render(<ProtectedImage imageId={5} alt="Complaint photo" />);

    expect(screen.getByRole('img', { name: 'Complaint photo' })).toHaveAttribute('aria-busy', 'true');
    await waitFor(() =>
      expect(screen.getByRole('img', { name: 'Complaint photo' })).toHaveAttribute('src', 'blob:photo-5'),
    );
    expect(authorization).toBe('Bearer photo-token');

    unmount();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:photo-5');
  });

  it('a 404 (not yours or missing) shows a placeholder, not a broken image', async () => {
    server.use(http.get('/api/v1/files/6', () => new HttpResponse(null, { status: 404 })));
    render(<ProtectedImage imageId={6} alt="Complaint photo" />);

    expect(await screen.findByText('Not found.')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Complaint photo' }).tagName).toBe('DIV');
  });
});
