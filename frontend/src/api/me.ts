import { z } from 'zod';
import { api, type RequestOptions } from '../lib/api';
import { roleSchema } from './auth';

// /me (docs/04_API_CONTRACT.md §2): always the caller's own row.

export const consentTypeSchema = z.enum(['PRIVACY_NOTICE', 'PUBLIC_PHOTO', 'AI_TRAINING', 'WHATSAPP_MESSAGES']);
export type ConsentType = z.output<typeof consentTypeSchema>;

export const meSchema = z.object({
  id: z.number(),
  fullName: z.string(),
  email: z.string().nullable(),
  phoneMasked: z.string().nullable(),
  role: roleSchema,
  preferredLanguage: z.string(),
  emailOptIn: z.boolean(),
  whatsappOptIn: z.boolean(),
  consents: z.array(
    z.object({ type: consentTypeSchema, granted: z.boolean(), noticeVersion: z.string().nullable(), at: z.string() }),
  ),
});
export type Me = z.output<typeof meSchema>;

export interface UpdateMeBody {
  fullName: string;
  preferredLanguage: string;
  emailOptIn: boolean;
  whatsappOptIn: boolean;
}

export const ME_QUERY_KEY = ['me'] as const;

export const meApi = {
  get: (options?: RequestOptions) => api.get('/me', meSchema, options),
  update: (body: UpdateMeBody) => api.put('/me', meSchema, body),
  consent: (consentType: ConsentType, granted: boolean) => api.post('/me/consents', meSchema, { consentType, granted }),
};
