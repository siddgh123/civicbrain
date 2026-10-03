import { useTranslation } from 'react-i18next';
import { PlaceholderPage } from '../components/PlaceholderPage';
import type en from '../i18n/en.json';

type PageKey = `pages.${Exclude<keyof typeof en.pages, 'track'>}`;

/** Route element for a screen that a later prompt fills in. */
export function TranslatedPlaceholder({ titleKey }: { titleKey: PageKey }) {
  const { t } = useTranslation();
  return <PlaceholderPage title={t(titleKey)} />;
}
