import { z } from 'zod';
import { api } from '../lib/api';

// /public (docs/04_API_CONTRACT.md §3): no auth, cached 60 s by the server.

export const privacyNoticeSchema = z.object({ version: z.string(), publishedAt: z.string(), summary: z.string() });
export type PrivacyNotice = z.output<typeof privacyNoticeSchema>;

export const PRIVACY_NOTICE_QUERY_KEY = ['public', 'privacy-notice'] as const;

export const publicApi = {
  privacyNotice: () => api.get('/public/privacy-notice', privacyNoticeSchema),
};
