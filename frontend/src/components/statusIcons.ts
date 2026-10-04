import type { ComponentType } from 'react';
import type { ComplaintStatus, StatusTone } from '../lib/complaintStatus';
import {
  CalendarIcon,
  CheckDoubleIcon,
  CheckIcon,
  ClipboardIcon,
  HammerIcon,
  InboxIcon,
  LinkIcon,
  RotateIcon,
  SearchIcon,
  UserCheckIcon,
  XIcon,
} from './icons/icons';
import type { IconProps } from './icons/Svg';

// Colour tokens from index.css (@theme --color-status-*); full class names so Tailwind finds them.
export const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: 'bg-status-neutral-bg text-status-neutral-fg border-status-neutral-border',
  info: 'bg-status-info-bg text-status-info-fg border-status-info-border',
  warning: 'bg-status-warning-bg text-status-warning-fg border-status-warning-border',
  success: 'bg-status-success-bg text-status-success-fg border-status-success-border',
  danger: 'bg-status-danger-bg text-status-danger-fg border-status-danger-border',
};

/** docs/05_UI_SPEC.md §1 icon per status (StatusBadge, Timeline). */
export const STATUS_ICON: Record<ComplaintStatus, ComponentType<IconProps>> = {
  SUBMITTED: InboxIcon,
  VERIFIED: SearchIcon,
  SCHEDULED: CalendarIcon,
  ASSIGNED: UserCheckIcon,
  INSPECTED: ClipboardIcon,
  IN_PROGRESS: HammerIcon,
  COMPLETED: CheckIcon,
  CLOSED: CheckDoubleIcon,
  REOPENED: RotateIcon,
  REJECTED: XIcon,
  MERGED: LinkIcon,
};
