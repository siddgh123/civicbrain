import type { ReactNode } from 'react';
import { AlertIcon } from '../../components/icons/icons';

interface MessageCardProps {
  title: string;
  text: string;
  action: ReactNode;
}

/** Centered title + sentence + one action, for 404 / no access / crash pages. */
export function MessageCard({ title, text, action }: MessageCardProps) {
  return (
    <section className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-2xl border border-slate-200 bg-white px-6 py-10 text-center shadow-sm">
      <AlertIcon className="size-10 text-slate-400" />
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      <p className="text-slate-700">{text}</p>
      {action}
    </section>
  );
}

export const actionClass =
  'inline-flex min-h-11 items-center justify-center rounded-lg bg-brand-700 px-5 font-semibold text-white hover:bg-brand-800';
