import type { ComponentType } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { BellIcon, CameraIcon, ScanIcon } from '../../components/icons/icons';
import type { IconProps } from '../../components/icons/Svg';
import { StatusBadge } from '../../components/StatusBadge';
import type { ComplaintStatus } from '../../lib/complaintStatus';

const button = 'inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-5 text-base font-semibold';

const STEPS: { icon: ComponentType<IconProps>; title: 'step1Title' | 'step2Title' | 'step3Title'; text: 'step1Text' | 'step2Text' | 'step3Text' }[] = [
  { icon: CameraIcon, title: 'step1Title', text: 'step1Text' },
  { icon: ScanIcon, title: 'step2Title', text: 'step2Text' },
  { icon: BellIcon, title: 'step3Title', text: 'step3Text' },
];

/** The path a complaint takes, shown as the real status badges (no complaint data). */
const JOURNEY: ComplaintStatus[] = ['SUBMITTED', 'VERIFIED', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CLOSED'];

/** docs/05_UI_SPEC.md §3 Landing: what CivicBrain does (3 steps) + Report a problem / Track / Log in. */
export function LandingPage() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-12 sm:gap-16">
      <section className="grid gap-10 md:grid-cols-[3fr_2fr] md:items-center">
        <div>
          <p className="text-sm font-semibold tracking-wide text-brand-700 uppercase">{t('app.council')}</p>
          <h1 className="mt-3 text-3xl leading-tight font-bold text-balance text-slate-900 sm:text-4xl">
            {t('landing.title')}
          </h1>
          <p className="mt-4 text-lg text-pretty text-slate-700">{t('landing.intro')}</p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Link
              to="/citizen/new"
              data-testid="landing-report"
              className={`${button} bg-brand-700 text-white shadow-sm hover:bg-brand-800`}
            >
              <CameraIcon className="size-5" />
              {t('landing.report')}
            </Link>
            <Link
              to="/citizen/complaints"
              data-testid="landing-track"
              className={`${button} bg-white text-brand-800 ring-1 ring-brand-700/40 hover:bg-brand-50`}
            >
              {t('landing.track')}
            </Link>
            <Link
              to="/login"
              data-testid="landing-login"
              className={`${button} text-slate-800 underline-offset-4 hover:underline`}
            >
              {t('landing.login')}
            </Link>
          </div>
        </div>
        <ol
          aria-hidden="true"
          className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          {JOURNEY.map((status, index) => (
            <li key={status} className="flex items-center gap-3">
              <span className="grid size-6 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                {index + 1}
              </span>
              <StatusBadge status={status} />
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="how-it-works">
        <h2 id="how-it-works" className="text-xl font-bold text-slate-900">
          {t('landing.stepsTitle')}
        </h2>
        <ol className="mt-5 grid gap-4 md:grid-cols-3">
          {STEPS.map(({ icon: Icon, title, text }, index) => (
            <li key={title} className="flex gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
                <Icon className="size-6" />
              </span>
              <div>
                <h3 className="font-semibold text-slate-900">
                  {index + 1}. {t(`landing.${title}`)}
                </h3>
                <p className="mt-1 text-slate-700">{t(`landing.${text}`)}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
