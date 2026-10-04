import { z } from 'zod';
import { api } from '../lib/api';
import { COMPLAINT_STATUSES } from '../lib/complaintStatus';

// /citizen (docs/04_API_CONTRACT.md §5): capture sessions, complaint submission and the caller's own complaints.
// Ownership is enforced by the server (another citizen's complaint is a 404).

export const complaintStatusSchema = z.enum(COMPLAINT_STATUSES);

export const DEPTH_ANSWERS = ['SHALLOW', 'FINGER', 'DEEP'] as const;
export type DepthAnswer = (typeof DEPTH_ANSWERS)[number];

export const captureSessionSchema = z.object({ captureSessionId: z.string(), expiresAt: z.string() });

export const submitResponseSchema = z.object({
  complaintId: z.number(),
  publicRef: z.string(),
  status: complaintStatusSchema,
  wardNumber: z.number().nullable(),
});
export type SubmitResponse = z.output<typeof submitResponseSchema>;

export const complaintListItemSchema = z.object({
  complaintId: z.number(),
  publicRef: z.string(),
  title: z.string(),
  categoryName: z.string().nullable(),
  status: complaintStatusSchema,
  wardNumber: z.number().nullable(),
  submittedAt: z.string(),
  thumbnailImageId: z.number().nullable(),
});
export type ComplaintListItem = z.output<typeof complaintListItemSchema>;

export const complaintPageSchema = z.object({
  items: z.array(complaintListItemSchema),
  page: z.number(),
  size: z.number(),
  totalItems: z.number(),
  totalPages: z.number(),
});
export type ComplaintPage = z.output<typeof complaintPageSchema>;

export const timelineEntrySchema = z.object({ status: complaintStatusSchema, at: z.string(), remarks: z.string().nullable() });
export type TimelineEntry = z.output<typeof timelineEntrySchema>;

export const complaintDetailSchema = complaintListItemSchema.extend({
  categoryId: z.number().nullable(),
  description: z.string(),
  landmark: z.string().nullable(),
  latitude: z.number(),
  longitude: z.number(),
  images: z.array(z.object({ imageId: z.number(), role: z.string() })),
  timeline: z.array(timelineEntrySchema),
  contractorName: z.string().nullable(),
  /** `YYYY-MM-DD` (the plan's date). */
  plannedDate: z.string().nullable(),
  mergedIntoPublicRef: z.string().nullable(),
  canGiveFeedback: z.boolean(),
});
export type ComplaintDetail = z.output<typeof complaintDetailSchema>;

/** The `data` part of POST /citizen/complaints (04 §5). Optional keys are left out, never sent as null. */
export interface ComplaintSubmission {
  categoryId: number;
  title: string;
  description: string;
  landmark?: string;
  latitude: number;
  longitude: number;
  locationAccuracyM: number;
  locationCapturedAt: string;
  devicePitchDeg?: number;
  deviceRollDeg?: number;
  captureSessionId: string;
  captureMethod: 'IN_APP_CAMERA' | 'FILE_CAPTURE';
  a4InFrame: boolean;
  depthAnswer?: DepthAnswer;
}

/** Page size for the citizen's own list: one request covers everyone below the 5-per-day limit for weeks. */
export const OWN_PAGE_SIZE = 100;

export const CITIZEN_COMPLAINTS_KEY = ['citizen', 'complaints'] as const;

export const citizenApi = {
  captureSession: () => api.post('/citizen/capture-sessions', captureSessionSchema),
  submit: (data: ComplaintSubmission, photo: Blob) => {
    const form = new FormData();
    form.append('data', new Blob([JSON.stringify(data)], { type: 'application/json' }), 'data.json');
    form.append('photo', photo, photo.type === 'image/png' ? 'photo.png' : 'photo.jpg');
    return api.postMultipart('/citizen/complaints', submitResponseSchema, form);
  },
  list: (page: number, size: number, signal?: AbortSignal) =>
    api.get('/citizen/complaints', complaintPageSchema, { query: { page, size }, signal }),
  detail: (id: number, signal?: AbortSignal) => api.get(`/citizen/complaints/${id}`, complaintDetailSchema, { signal }),
};

/** At most this many merged complaints are opened while looking for the one linked to a reference. */
const MAX_MERGED_LOOKUPS = 20;

/**
 * The id of the caller's complaint with this `publicRef`; with `followMerged`, otherwise the caller's MERGED complaint
 * that is linked to it (status mails for a merged report carry the master's track link). `null` = none of the caller's.
 */
export async function findOwnComplaintId(
  publicRef: string,
  options: { followMerged: boolean; signal?: AbortSignal },
): Promise<number | null> {
  const merged: number[] = [];
  for (let page = 0; ; page += 1) {
    const result = await citizenApi.list(page, OWN_PAGE_SIZE, options.signal);
    const hit = result.items.find((item) => item.publicRef === publicRef);
    if (hit) return hit.complaintId;
    merged.push(...result.items.filter((item) => item.status === 'MERGED').map((item) => item.complaintId));
    if (page + 1 >= result.totalPages) break;
  }
  if (!options.followMerged) return null;
  for (const id of merged.slice(0, MAX_MERGED_LOOKUPS)) {
    const detail = await citizenApi.detail(id, options.signal);
    if (detail.mergedIntoPublicRef === publicRef) return id;
  }
  return null;
}
