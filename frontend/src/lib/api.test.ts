import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import { setAccessToken } from '../auth/tokenStore';
import { server } from '../test/server';
import { api, ApiError } from './api';

const PROBLEM_HEADERS = { 'Content-Type': 'application/problem+json' };

async function caught(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.then(
    () => {
      throw new Error('expected the request to fail');
    },
    (e: unknown) => e,
  );
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

describe('api client', () => {
  it('turns a 422 problem+json into ApiError with code, message (= detail), fieldErrors and requestId', async () => {
    server.use(
      http.post('/api/v1/citizen/complaints', () =>
        HttpResponse.json(
          {
            type: 'https://civicbrain.app/errors/GPS_ACCURACY_TOO_LOW',
            title: 'Location is not accurate enough',
            status: 422,
            code: 'GPS_ACCURACY_TOO_LOW',
            detail: 'Accuracy was 240 m; 150 m or better is needed.',
            requestId: '7f3a',
            fieldErrors: [{ field: 'locationAccuracyM', code: 'MAX', message: 'must be ≤ 150' }],
          },
          { status: 422, headers: PROBLEM_HEADERS },
        ),
      ),
    );

    const error = await caught(api.post('/citizen/complaints', z.unknown(), { title: 'x' }));

    expect(error.status).toBe(422);
    expect(error.code).toBe('GPS_ACCURACY_TOO_LOW');
    expect(error.message).toBe('Accuracy was 240 m; 150 m or better is needed.');
    expect(error.requestId).toBe('7f3a');
    expect(error.fieldErrors).toEqual([{ field: 'locationAccuracyM', code: 'MAX', message: 'must be ≤ 150' }]);
  });

  it('parses a 2xx JSON body with the schema and sends the in-memory bearer token', async () => {
    let authorization: string | null = null;
    server.use(
      http.get('/api/v1/public/categories', ({ request }) => {
        authorization = request.headers.get('authorization');
        return HttpResponse.json([{ id: 1, name: 'Pothole' }]);
      }),
    );
    setAccessToken('abc.def.ghi');

    const data = await api.get('/public/categories', z.array(z.object({ id: z.number(), name: z.string() })));

    expect(data).toEqual([{ id: 1, name: 'Pothole' }]);
    expect(authorization).toBe('Bearer abc.def.ghi');
  });

  it('sends no Authorization header without a token and adds query parameters (skipping empty ones)', async () => {
    let seen: { authorization: string | null; search: string } | null = null;
    server.use(
      http.get('/api/v1/citizen/complaints', ({ request }) => {
        seen = { authorization: request.headers.get('authorization'), search: new URL(request.url).search };
        return HttpResponse.json([]);
      }),
    );

    await api.get('/citizen/complaints', z.array(z.unknown()), { query: { page: 2, status: undefined, size: 20 } });

    expect(seen).toEqual({ authorization: null, search: '?page=2&size=20' });
  });

  it('sends JSON bodies as application/json and multipart without a hand-made content type', async () => {
    const seen: string[] = [];
    server.use(
      http.post('/api/v1/echo', async ({ request }) => {
        seen.push(request.headers.get('content-type') ?? '');
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const form = new FormData();
    form.append('data', new Blob([JSON.stringify({ a: 1 })], { type: 'application/json' }));

    await api.post('/echo', null, { a: 1 });
    await api.postMultipart('/echo', null, form);

    expect(seen[0]).toBe('application/json');
    expect(seen[1]).toMatch(/^multipart\/form-data; boundary=/);
  });

  it('a body without problem+json falls back to a code by HTTP status and the X-Request-Id header', async () => {
    server.use(
      http.get('/api/v1/officer/complaints', () =>
        new HttpResponse('Bad Gateway', { status: 502, headers: { 'X-Request-Id': 'rid-502' } }),
      ),
    );

    const error = await caught(api.get('/officer/complaints', z.unknown()));

    expect(error.status).toBe(502);
    expect(error.code).toBe('DEPENDENCY_UNAVAILABLE');
    expect(error.requestId).toBe('rid-502');
    expect(error.fieldErrors).toEqual([]);
  });

  it('reads Retry-After for 429', async () => {
    server.use(
      http.post('/api/v1/auth/login', () =>
        HttpResponse.json(
          { status: 429, code: 'RATE_LIMITED', title: 'Too many requests', requestId: 'r1' },
          { status: 429, headers: { ...PROBLEM_HEADERS, 'Retry-After': '30' } },
        ),
      ),
    );

    const error = await caught(api.post('/auth/login', z.unknown(), { identifier: 'a', password: 'b' }));

    expect(error.code).toBe('RATE_LIMITED');
    expect(error.retryAfterSeconds).toBe(30);
  });

  it('a network failure becomes ApiError NETWORK_ERROR with status 0', async () => {
    server.use(http.get('/api/v1/public/wards', () => HttpResponse.error()));

    const error = await caught(api.get('/public/wards', z.unknown()));

    expect(error.status).toBe(0);
    expect(error.code).toBe('NETWORK_ERROR');
  });

  it('a 2xx body that does not match the schema becomes UNEXPECTED_RESPONSE (never passed on unchecked)', async () => {
    server.use(http.get('/api/v1/me', () => HttpResponse.json({ id: 'not-a-number' })));

    const error = await caught(api.get('/me', z.object({ id: z.number() })));

    expect(error.code).toBe('UNEXPECTED_RESPONSE');
  });
});
