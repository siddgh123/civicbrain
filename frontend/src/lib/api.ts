import { z } from 'zod';
import { getAccessToken } from '../auth/tokenStore';

// Typed fetch wrapper for /api/v1 (docs/04_API_CONTRACT.md, docs/12_ERROR_HANDLING.md §1, §6). Every non-2xx answer
// becomes an ApiError; every 2xx body is parsed with a zod schema before the app sees it (rule 20: no `any`).
// P07 adds the 401 -> shared refresh -> retry-once step here.

export const API_BASE = '/api/v1';

export interface FieldError {
  field: string;
  code: string;
  message: string;
}

export interface ApiErrorInit {
  status: number;
  code: string;
  message: string;
  fieldErrors?: FieldError[];
  requestId?: string | null;
  retryAfterSeconds?: number | null;
}

/** A failed API call. `message` is the problem's `detail` (for logs/devs); the UI shows `errors.<code>` instead. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: FieldError[];
  readonly requestId: string | null;
  readonly retryAfterSeconds: number | null;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = 'ApiError';
    this.status = init.status;
    this.code = init.code;
    this.fieldErrors = init.fieldErrors ?? [];
    this.requestId = init.requestId ?? null;
    this.retryAfterSeconds = init.retryAfterSeconds ?? null;
  }
}

const problemSchema = z.object({
  title: z.string().optional(),
  code: z.string().optional(),
  detail: z.string().optional(),
  requestId: z.string().optional(),
  fieldErrors: z
    .array(z.object({ field: z.string(), code: z.string(), message: z.string() }))
    .optional(),
});

type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  query?: Record<string, QueryValue>;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /** `include` only for the refresh/logout calls that need the `__Host-cb_rt` cookie (P07). */
  credentials?: RequestCredentials;
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
type Body = { kind: 'json'; value: unknown } | { kind: 'form'; value: FormData } | undefined;

/** Code when the body is not a problem document (proxy error page, empty body). */
function codeForStatus(status: number): string {
  if (status === 401) return 'UNAUTHENTICATED';
  if (status === 403) return 'FORBIDDEN';
  if (status === 404) return 'NOT_FOUND';
  if (status === 413) return 'FILE_TOO_LARGE';
  if (status === 429) return 'RATE_LIMITED';
  if (status === 502 || status === 503 || status === 504) return 'DEPENDENCY_UNAVAILABLE';
  if (status >= 500) return 'INTERNAL_ERROR';
  return 'MALFORMED_REQUEST';
}

function parseRetryAfter(value: string | null): number | null {
  if (value === null || !/^\d+$/.test(value.trim())) return null;
  return Number(value.trim());
}

async function toApiError(response: Response): Promise<ApiError> {
  const headerRequestId = response.headers.get('X-Request-Id');
  const retryAfterSeconds = parseRetryAfter(response.headers.get('Retry-After'));
  let problem: z.infer<typeof problemSchema> | null = null;
  if ((response.headers.get('Content-Type') ?? '').includes('json')) {
    const parsed = problemSchema.safeParse(await response.json().catch(() => null));
    problem = parsed.success ? parsed.data : null;
  }
  return new ApiError({
    status: response.status,
    code: problem?.code ?? codeForStatus(response.status),
    message: problem?.detail ?? problem?.title ?? `HTTP ${response.status}`,
    fieldErrors: problem?.fieldErrors ?? [],
    requestId: problem?.requestId ?? headerRequestId,
    retryAfterSeconds,
  });
}

function buildUrl(path: string, query: RequestOptions['query']): URL {
  const url = new URL(API_BASE + path, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.append(key, String(value));
  }
  return url;
}

/** What a call resolves to: the schema's output, or nothing when the schema is `null`. */
type Result<S> = S extends z.ZodType ? z.output<S> : void;

async function request(
  method: Method,
  path: string,
  schema: z.ZodType | null,
  body: Body,
  options: RequestOptions = {},
): Promise<unknown> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json, application/problem+json');
  const token = getAccessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  let payload: BodyInit | undefined;
  if (body?.kind === 'json') {
    headers.set('Content-Type', 'application/json');
    payload = JSON.stringify(body.value);
  } else if (body?.kind === 'form') {
    payload = body.value; // the browser sets multipart/form-data with its boundary
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      headers,
      body: payload,
      signal: options.signal,
      credentials: options.credentials ?? 'same-origin',
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') throw cause; // TanStack Query cancellation
    throw new ApiError({ status: 0, code: 'NETWORK_ERROR', message: 'Network request failed' });
  }

  if (!response.ok) throw await toApiError(response);
  if (schema === null || response.status === 204) return undefined;

  const parsed = schema.safeParse(await response.json().catch(() => undefined));
  if (!parsed.success) {
    throw new ApiError({
      status: response.status,
      code: 'UNEXPECTED_RESPONSE',
      message: `Response of ${method} ${path} does not match the expected shape`,
      requestId: response.headers.get('X-Request-Id'),
    });
  }
  return parsed.data;
}

/**
 * Call with a zod schema to get the parsed body, or with `null` when the answer has no body (204).
 * Paths are relative to /api/v1, e.g. `api.get('/public/categories', categoriesSchema)`.
 */
export const api = {
  get<S extends z.ZodType>(path: string, schema: S, options?: RequestOptions): Promise<z.output<S>> {
    return request('GET', path, schema, undefined, options) as Promise<z.output<S>>;
  },
  post<S extends z.ZodType | null>(path: string, schema: S, json?: unknown, options?: RequestOptions) {
    const body: Body = json === undefined ? undefined : { kind: 'json', value: json };
    return request('POST', path, schema, body, options) as Promise<Result<S>>;
  },
  put<S extends z.ZodType | null>(path: string, schema: S, json: unknown, options?: RequestOptions) {
    return request('PUT', path, schema, { kind: 'json', value: json }, options) as Promise<Result<S>>;
  },
  delete<S extends z.ZodType | null>(path: string, schema: S, options?: RequestOptions) {
    return request('DELETE', path, schema, undefined, options) as Promise<Result<S>>;
  },
  postMultipart<S extends z.ZodType | null>(path: string, schema: S, form: FormData, options?: RequestOptions) {
    return request('POST', path, schema, { kind: 'form', value: form }, options) as Promise<Result<S>>;
  },
};
