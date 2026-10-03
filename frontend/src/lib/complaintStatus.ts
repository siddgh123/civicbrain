// The 11 values of the ck_complaints_status CHECK (docs/03_DATABASE.md §3.10) and their badge tone
// (docs/05_UI_SPEC.md §1). Labels are i18n keys `status.<STATUS>`; icons are mapped in components/StatusBadge.
export const COMPLAINT_STATUSES = [
  'SUBMITTED',
  'VERIFIED',
  'SCHEDULED',
  'ASSIGNED',
  'INSPECTED',
  'IN_PROGRESS',
  'COMPLETED',
  'CLOSED',
  'REOPENED',
  'REJECTED',
  'MERGED',
] as const;

export type ComplaintStatus = (typeof COMPLAINT_STATUSES)[number];

export type StatusTone = 'neutral' | 'info' | 'warning' | 'success' | 'danger';

export const STATUS_TONE: Record<ComplaintStatus, StatusTone> = {
  SUBMITTED: 'neutral',
  VERIFIED: 'neutral',
  SCHEDULED: 'info',
  ASSIGNED: 'info',
  INSPECTED: 'info',
  IN_PROGRESS: 'warning',
  COMPLETED: 'success',
  CLOSED: 'success',
  REOPENED: 'warning',
  REJECTED: 'danger',
  MERGED: 'neutral',
};
