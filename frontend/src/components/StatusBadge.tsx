import { useTranslation } from 'react-i18next';
import { STATUS_TONE, type ComplaintStatus } from '../lib/complaintStatus';
import { STATUS_ICON, TONE_CLASSES } from './statusIcons';

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
