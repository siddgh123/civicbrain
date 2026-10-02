# P05 — Frontend skeleton
**Day 1–2 · agent ≈ 1.5 h · human 0 min · Needs: P01 (P04 for the API proxy check) · Model: Flash is fine**

## Goal
`frontend/` builds, lints, type-checks and tests with the pinned packages; the three portal shells, router,
Tailwind, i18n (en), API client, auth context placeholder and the shared status badge exist; Vite serves the
app on 5173 and proxies `/api` to the backend.

## Read first
`.agents/rules/20-frontend-react.md` · `docs/05_UI_SPEC.md` §1, §2, §7, §8 · `docs/12_ERROR_HANDLING.md` §6 ·
`docs/09_BUILD_PLAN.md` P0 step 5 (frontend part) · `frontend/package.json` (do NOT change it)

## Build
1. Do **not** run `npm create vite`. In `frontend`: `npm install` (creates `package-lock.json` - commit it; never edit
   versions). If `npm install` reports a peer conflict: stop and ask (do not use `--force`).
2. Write by hand: `index.html`, `src/main.tsx`, `src/App.tsx`, `src/index.css` (`@import "tailwindcss";` + colour tokens
   for the status colours of 05 §1), `vite.config.ts` (`@vitejs/plugin-react`, `@tailwindcss/vite`, `server.port 5173`,
   `strictPort`, proxy `/api` → `http://localhost:8080` with `changeOrigin: false`, `server.allowedHosts: ['.trycloudflare.com']`),
   `vitest.config.ts` (jsdom, `src/test/setup.ts` with jest-dom + MSW server, `test.include: ['src/**/*.test.{ts,tsx}']`,
   `test.exclude: ['node_modules', 'e2e', 'walkthrough', 'playwright-report', 'test-results']` so Vitest never picks up
   the Playwright specs in `frontend/walkthrough/` or P26's `frontend/e2e/`), `tsconfig.json` / `tsconfig.app.json` /
   `tsconfig.node.json` (strict), `eslint.config.js` (flat config: @eslint/js, typescript-eslint, react-hooks, react-refresh).
3. `src/lib/api.ts`: fetch wrapper (base `/api/v1`, bearer from the auth context, JSON + multipart, parses RFC 9457
   problems into `ApiError{status, code, message, fieldErrors, requestId}` (12 §6; `message` = the problem's `detail`); GET retry rules of 05 §2 belong to TanStack
   Query defaults in `src/lib/queryClient.ts`).
4. `src/auth/AuthProvider.tsx` placeholder (state shape `{user, accessToken}`, `login/logout` stubs) - completed in P07.
5. `src/i18n/` with i18next + react-i18next, `en.json` (all UI strings via keys; error messages `errors.<CODE>` from 12 §2).
6. Router (react-router 7): `/` landing, `/login`, `/register`, `/citizen/*`, `/officer/*`, `/contractor/*`, `/c/:publicRef`
   (track link from messages → login then detail), 404 page. Layouts: `CitizenLayout` + `ContractorLayout` (mobile-first,
   bottom nav), `OfficerLayout` (desktop left nav of 05 §5). Guards `RequireAuth`, `RequireRole` (UX only).
7. Shared components (05 §7, first versions): `StatusBadge` (text + icon + colour token for all 11 statuses, 05 §1),
   inline SVG icons in `src/components/icons/`, `EmptyState`, `ErrorState` (code → message + requestId), `PageSkeleton`,
   `Toast` (aria-live). `data-testid` names of 05 §8 where they already exist.
8. Landing page per 05 §3 (3 steps, buttons Report / Track / Log in).

## Tests (write first)
- `StatusBadge.test.tsx`: every status renders its label text and an icon (not colour only).
- `App.test.tsx`: `/` renders the landing heading; unknown route shows the 404 page; `/officer` without login redirects to `/login`.
- `api.test.ts` (MSW): a problem+json 422 becomes `ApiError` with `code` and `fieldErrors`.

## Verify (agent)
1. in `frontend`: `npm run lint` · `npm run typecheck` · `npm test -- --run` · `npm run build`.
2. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only frontend` → healthy.
3. Browser tool: open http://localhost:5173 (desktop) and with a 390 px wide window; screenshots
   `docs/screenshots/P05_landing_desktop.png`, `P05_landing_mobile.png`; open http://localhost:5173/api/v1/public/categories
   → 401/404 JSON from the backend (proves the proxy; the endpoint comes in P10).

## Ask the human (yes/no)
- Q1. Open http://localhost:5173 on the laptop - do you see the CivicBrain landing page with "Report a problem"?
- Q2. Do the two screenshots look clean on desktop and on the narrow (phone) width?

## Done when
4 checks green · Vite healthy · `package-lock.json` committed · pushed.

## Next
Day 2: `/run-prompt P06` — authentication backend (≈ 3 h, strongest model)
