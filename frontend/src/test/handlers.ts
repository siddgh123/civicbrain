import type { RequestHandler } from 'msw';

// Default MSW handlers shared by all tests (none yet). Tests add their own with `server.use(...)`.
export const handlers: RequestHandler[] = [];
