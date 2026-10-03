import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';
import { STATUS_TONE, type ComplaintStatus, type StatusTone } from '../lib/complaintStatus';
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

const STATUS_ICON: Record<ComplaintStatus, ComponentType<IconProps>> = {
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

// Colour tokens from index.css (@theme --color-status-*); full class names so Tailwind finds them.
const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: 'bg-status-neutral-bg text-status-neutral-fg border-status-neutral-border',
  info: 'bg-status-info-bg text-status-info-fg border-status-info-border',
  warning: 'bg-status-warning-bg text-status-warning-fg border-status-warning-border',
  success: 'bg-status-success-bg text-status-success-fg border-status-success-border',
  danger: 'bg-status-danger-bg text-status-danger-fg border-status-danger-border',
};

interface StatusBadgeProps {
  status: ComplaintStatus;
  /** For MERGED: the master's `CB-xxxxxx` ("Linked to CB-000123"). */
  mergedIntoPublicRef?: string | null;
}

/** Complaint status as text + icon + colour (never colour alone), docs/05_UI_SPEC.md §1. */
export function StatusBadge({ status, mergedIntoPublicRef }: StatusBadgeProps) {
  const { t } = useTranslation();
  const tone = STATUS_TONE[status];
  const Icon = STATUS_ICON[status];
  const label = t(`status.${status}`, {
    publicRef: mergedIntoPublicRef ?? t('statusExtra.anotherComplaint'),
  });
  return (
    <span
      data-testid="status-badge"
      data-status={status}
      data-tone={tone}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-sm font-medium ${TONE_CLASSES[tone]}`}
    >
      <Icon className="size-4 shrink-0" />
      {label}
    </span>
  );
}
