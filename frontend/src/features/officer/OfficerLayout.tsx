import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet, useNavigate } from 'react-router';
import { useAuth } from '../../auth/useAuth';
import { Brand } from '../../components/Brand';
import { GridIcon, ListIcon, LogoutIcon, RouteIcon, ShieldIcon, UsersIcon } from '../../components/icons/icons';
import type { IconProps } from '../../components/icons/Svg';
import { SkipLink } from '../../components/SkipLink';

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<IconProps>;
  end?: boolean;
}

/**
 * Desktop shell (docs/05_UI_SPEC.md §5): left nav + top bar. MVP nav: Duplicates queue and Notifications log are
 * Phase 2 (09_BUILD_PLAN_7DAY §1 OUT); Admin = officers & scopes, ADMIN only. The scope chip comes with P14.
 */
export function OfficerLayout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const items: NavItem[] = [
    { to: '/officer', label: t('nav.officer.dashboard'), icon: GridIcon, end: true },
    { to: '/officer/complaints', label: t('nav.officer.complaints'), icon: ListIcon },
    { to: '/officer/plans', label: t('nav.officer.plans'), icon: RouteIcon },
    { to: '/officer/contractors', label: t('nav.officer.contractors'), icon: UsersIcon },
  ];
  if (user?.role === 'ADMIN') items.push({ to: '/officer/admin', label: t('nav.officer.admin'), icon: ShieldIcon });

  const onLogout = () => {
    void navigate('/', { replace: true });
    void logout();
  };

  return (
    <div className="flex min-h-dvh bg-slate-50">
      <SkipLink />
      <aside className="sticky top-0 flex h-dvh w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex h-16 items-center px-5">
          <Brand to="/officer" />
        </div>
        <nav aria-label={t('nav.main')} className="flex-1 px-3 py-2">
          <ul className="flex flex-col gap-1">
            {items.map(({ to, label, icon: Icon, end }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `flex min-h-11 items-center gap-3 rounded-lg px-3 font-medium ${
                      isActive ? 'bg-brand-50 text-brand-800' : 'text-slate-700 hover:bg-slate-100'
                    }`
                  }
                >
                  <Icon className="size-5" />
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white px-6">
          <p className="truncate text-sm text-slate-600">{t('app.council')}</p>
          <div className="flex items-center gap-3">
            {user && (
              <p className="text-right text-sm leading-tight">
                <span className="block font-medium text-slate-900">{user.fullName}</span>
                <span className="block text-slate-600">{t(`roles.${user.role}`)}</span>
              </p>
            )}
            <button
              type="button"
              onClick={onLogout}
              data-testid="logout"
              className="flex min-h-11 items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-100"
            >
              <LogoutIcon className="size-4" />
              {t('common.logout')}
            </button>
          </div>
        </header>
        <main id="main" className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
