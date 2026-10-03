import 'i18next';
import type en from './en.json';

// Typed keys: `t('landing.title')` is checked by `tsc`, a missing key fails the typecheck.
declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'translation';
    resources: { translation: typeof en };
  }
}
