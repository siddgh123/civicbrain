import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import { defineConfig, globalIgnores } from 'eslint/config';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default defineConfig([
  globalIgnores(['dist', 'coverage', 'playwright-report', 'test-results']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
    rules: {
      // rule 20: no `any` (parse unknown with zod at the API boundary)
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      // docs/05_UI_SPEC.md §2 + rule 20: no raw HTML injection, no eval
      'no-restricted-properties': [
        'error',
        { property: 'dangerouslySetInnerHTML', message: 'Not allowed (docs/05_UI_SPEC.md §2).' },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: 'Not allowed (docs/05_UI_SPEC.md §2).',
        },
      ],
      'no-eval': 'error',
      'no-implied-eval': 'error',
    },
  },
  {
    files: ['*.config.{ts,js}', 'walkthrough/**/*.ts', 'e2e/**/*.ts'],
    languageOptions: { globals: globals.node },
  },
]);
