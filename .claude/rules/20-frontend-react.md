---
paths:
  - "frontend/**"
---
<!-- Generated from .agents/rules/20-frontend-react.md by scripts/dev/sync-claude.ps1. Edit the source, then run the script. -->
# Frontend rules (React 19 + TypeScript 6.0 + Vite 8 + Tailwind 4)

- Use the pinned versions in `frontend/package.json`. TypeScript stays 6.0.x (typescript-eslint supports < 6.1); Leaflet stays 1.9.x (react-leaflet 5); Tailwind 4 via `@tailwindcss/vite` (no `tailwind.config.js`). Install new packages only with an exact version after approval.
- Structure: `src/app` (router, providers), `src/api` (typed client + TanStack Query hooks per resource, types mirroring `docs/04_API_CONTRACT.md`), `src/auth`, `src/components` (shared, `docs/05_UI_SPEC.md` §7), `src/features/{citizen,officer,contractor,admin,public}`, `src/i18n` (`en.json`, keys only in components), `src/test` (MSW handlers, render helpers).
- `strict: true`, no `any` (use `unknown` + zod parsing at the API boundary), no default exports except route components and tool config files (`vite.config.ts`, `vitest.config.ts`, `playwright.config.ts`, `eslint.config.js`).
- No extra UI packages without approval: icons are inline SVG components, marker grouping and list reordering are hand-written (`docs/05_UI_SPEC.md`).
- Access token only in memory; refresh via `POST /api/v1/auth/refresh` with `credentials: 'include'` and header `X-CB-CSRF: 1`; single shared refresh promise; `BroadcastChannel('cb-auth')` for logout sync. Never use localStorage/sessionStorage for tokens or personal data.
- Every page implements loading / empty / error / success states; error messages come from `errors.<code>` i18n keys (`docs/12_ERROR_HANDLING.md` §2, §6).
- Forms: react-hook-form + zod; show server `fieldErrors` on the fields; disable submit while pending.
- No `dangerouslySetInnerHTML`, no inline scripts, no `eval`; images from the API via `ProtectedImage` (blob URLs revoked on unmount).
- Mobile-first for citizen and contractor (test at 360 px); touch targets ≥ 44 px; labels for every input; `data-testid` on elements listed in `docs/05_UI_SPEC.md` §8.
- `CameraCapture` is the only way to take complaint/inspection/completion photos (getUserMedia + DeviceOrientation + Geolocation; fallback `<input type="file" accept="image/*" capture="environment">`; no gallery picker).
- Dev server (`vite.config.ts`): proxy `/api` to `http://localhost:8080` (same origin, no CORS), `server: { port: 5173, strictPort: true, allowedHosts: ['.trycloudflare.com'] }` so phones can use the Cloudflare quick tunnel (Vite blocks unknown Host headers otherwise).
- Tests: Vitest + Testing Library + MSW for components/hooks; Playwright for flows (`docs/08_TEST_PLAN.md` §4; fixtures in the repo-root `tests/fixtures/images/`, fake camera path made absolute with `import.meta.dirname`; accounts from `.env.test` via Node's built-in `process.loadEnvFile('../.env.test')` — no dotenv package — never hard-coded; `workers: 1`). `npm run lint && npm run typecheck && npm test -- --run` green before commit.
