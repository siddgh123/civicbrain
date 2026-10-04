import { z } from 'zod';
import { api } from '../lib/api';

// /public (docs/04_API_CONTRACT.md §3): no auth, cached 60 s by the server.

export const privacyNoticeSchema = z.object({ version: z.string(), publishedAt: z.string(), summary: z.string() });
export type PrivacyNotice = z.output<typeof privacyNoticeSchema>;

export const categorySchema = z.object({
  id: z.number(),
  name: z.string(),
  workTypeCode: z.string().nullable(),
  citizenSelectable: z.boolean(),
  /** Pothole and Waterlogging (V5): the wizard asks the depth question. */
  needsDepthAnswer: z.boolean(),
});
export type Category = z.output<typeof categorySchema>;

export const PRIVACY_NOTICE_QUERY_KEY = ['public', 'privacy-notice'] as const;
export const CATEGORIES_QUERY_KEY = ['public', 'categories'] as const;

export const publicApi = {
  privacyNotice: () => api.get('/public/privacy-notice', privacyNoticeSchema),
  categories: (signal?: AbortSignal) => api.get('/public/categories', z.array(categorySchema), { signal }),
};
