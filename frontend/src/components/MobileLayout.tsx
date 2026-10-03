import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet, useNavigate } from 'react-router';
import { useAuth } from '../auth/useAuth';
import { Brand } from './Brand';
import { LogoutIcon } from './icons/icons';
import type { IconProps } from './icons/Svg';
import { SkipLink } from './SkipLink';

export interface MobileNavItem {
  to: string;
  label: string;
  icon: ComponentType<IconProps>;
  /** Only active on the exact path (for the portal's index route). */
  end?: boolean;
  testId: string;
}

/** Mobile-first shell for the citizen and contractor portals: top bar + content + bottom navigation (05 §4, §6). */
export function MobileLayout({ homePath, items }: { homePath: string; items: MobileNavItem[] }) {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const navigate = useNavigate();

  // Leave the portal first: signing out while still on a portal page would make its guard redirect to the login.
  // flushSync commits the landing page now (React Router otherwise renders it in a transition, after the sign-out).
  const onLogout = async () => {
    await navigate('/', { replace: true, flushSync: true });
    await logout();
  };

  return (
    <div className="min-h-dvh bg-slate-50 pb-[calc(4.5rem+env(safe-area-inset-bottom))]">
      <SkipLink />
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 max-w-2xl items-center justify-between px-4">
          <Brand to={homePath} />
          <button
            type="button"
            onClick={() => void onLogout()}
            data-testid="logout"
            className="-mr-2 flex min-h-11 items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            <LogoutIcon className="size-4" />
            {t('common.logout')}
          </button>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-2xl px-4 py-5">
        <Outlet />
      </main>
      <nav
        aria-label={t('nav.main')}
        className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)]"
      >
        <ul className="mx-auto flex max-w-2xl">
          {items.map(({ to, label, icon: Icon, end, testId }) => (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                end={end}
                data-testid={testId}
                className={({ isActive }) =>
                  `flex min-h-16 flex-col items-center justify-center gap-0.5 text-xs font-medium ${
                    isActive ? 'text-brand-700' : 'text-slate-600 hover:text-slate-900'
                  }`
                }
              >
                <Icon className="size-6" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
