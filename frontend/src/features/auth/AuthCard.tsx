import type { ReactNode } from 'react';

interface AuthCardProps {
  title: string;
  intro?: ReactNode;
  children: ReactNode;
}

/** Narrow card for the public auth screens (mobile-first, 360 px). */
export function AuthCard({ title, intro, children }: AuthCardProps) {
  return (
    <section className="mx-auto flex w-full max-w-md flex-col gap-6 rounded-2xl border border-slate-200 bg-white px-5 py-7 shadow-sm sm:px-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        {intro && <p className="text-slate-700">{intro}</p>}
      </div>
      {children}
    </section>
  );
}
