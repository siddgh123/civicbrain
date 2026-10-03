import { useTranslation } from 'react-i18next';

/** First focusable element of every layout; jumps over the navigation to `<main id="main">`. */
export function SkipLink() {
  const { t } = useTranslation();
  return (
    <a
      href="#main"
      className="sr-only rounded-lg bg-white px-4 py-2 font-medium text-brand-800 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50"
    >
      {t('app.skipToContent')}
    </a>
  );
}
