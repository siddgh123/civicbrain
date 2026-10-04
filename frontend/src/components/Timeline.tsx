import { useTranslation } from 'react-i18next';
import type { TimelineEntry } from '../api/citizenComplaints';
import { STATUS_TONE } from '../lib/complaintStatus';
import { formatDateTime } from '../lib/format';
import { STATUS_ICON, TONE_CLASSES } from './statusIcons';

interface TimelineProps {
  entries: readonly TimelineEntry[];
  /** Accessible name of the list, e.g. "Progress". */
  label: string;
  /** For a MERGED entry: "Linked to CB-…". */
  mergedIntoPublicRef?: string | null;
}

/**
 * Vertical status timeline, newest first, with the remarks of each change (docs/05_UI_SPEC.md §4.7, §7). Every
 * entry has text + icon (never colour alone, §1).
 */
export function Timeline({ entries, label, mergedIntoPublicRef }: TimelineProps) {
  const { t } = useTranslation();
  // newest first; Array.sort is stable, so entries with the same time keep the server's order
  const sorted = [...entries].sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
  return (
    <ol aria-label={label} className="flex flex-col">
      {sorted.map((entry, index) => {
        const Icon = STATUS_ICON[entry.status];
        const last = index === sorted.length - 1;
        return (
          <li key={`${entry.status}-${entry.at}-${index}`} className="relative flex gap-3 pb-5 last:pb-0">
            {!last && <span aria-hidden="true" className="absolute top-9 bottom-0 left-[17px] w-0.5 bg-slate-200" />}
            <span
              data-status={entry.status}
              className={`z-10 grid size-9 shrink-0 place-items-center rounded-full border ${TONE_CLASSES[STATUS_TONE[entry.status]]}`}
            >
              <Icon className="size-4" />
            </span>
            <div className="flex min-w-0 flex-col gap-0.5 pt-1.5">
              <p className="font-semibold text-slate-900">
                {t(`status.${entry.status}`, {
                  publicRef: mergedIntoPublicRef ?? t('statusExtra.anotherComplaint'),
                })}
              </p>
              <time dateTime={entry.at} className="text-sm text-slate-600">
                {formatDateTime(entry.at)}
              </time>
              {entry.remarks && <p className="break-words text-slate-700">{entry.remarks}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
