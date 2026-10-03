import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { homePathForRole } from '../../auth/authContext';
import { useAuth } from '../../auth/useAuth';
import { Brand } from '../../components/Brand';
import { SkipLink } from '../../components/SkipLink';

/** Header + footer around the public pages (landing, login, register, privacy, 404, no access). */
export function PublicShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  return (
    <div className="flex min-h-dvh flex-col bg-slate-50">
      <SkipLink />
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4">
          <Brand />
          {user && (
            <Link
              to={homePathForRole(user.role)}
              className="flex min-h-11 items-center rounded-lg px-3 font-medium text-brand-800 hover:bg-brand-50"
            >
              {t('errorPages.goToMyPortal')}
            </Link>
          )}
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:py-12">
        {children}
      </main>
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-6 text-sm text-slate-600 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-1">
            <p>{t('landing.limits')}</p>
            <p>
              {t('landing.prototype')} · {t('app.council')}
            </p>
          </div>
          <Link
            to="/privacy"
            className="flex min-h-11 shrink-0 items-center font-medium text-brand-800 underline underline-offset-2 sm:min-h-0"
          >
            {t('landing.privacy')}
          </Link>
        </div>
      </footer>
    </div>
  );
}
