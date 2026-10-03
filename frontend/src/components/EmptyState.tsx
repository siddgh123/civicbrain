import type { ReactNode } from 'react';
import { InboxIcon } from './icons/icons';

interface EmptyStateProps {
  /** One sentence (docs/05_UI_SPEC.md §2). */
  message: string;
  /** The next action, e.g. a "Report a problem" link. */
  action?: ReactNode;
}

export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
      <InboxIcon className="size-8 text-slate-400" />
      <p className="text-slate-700">{message}</p>
      {action}
    </div>
  );
}
