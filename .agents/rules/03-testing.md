---
trigger: always_on
---

# Testing discipline

- Every task = plan → tests → code → run → record. Write the failing test first when fixing a bug.
- **7-day MVP mode (until 7 Oct 2026):** the mandatory tests are the list in `docs/09_BUILD_PLAN_7DAY.md` §4 (plus the DB tests); other suites in `docs/08_TEST_PLAN.md` are Phase 2. Instead of authorization-matrix rows, every new endpoint that returns someone's data gets one "other user → 404" test. All other rules below still apply.
- "Done" only after running the component's verify commands yourself (one command per call) and seeing them green in this session: backend `.\mvnw.cmd -q verify`; frontend `npm run lint`, `npm run typecheck`, `npm test -- --run`; AI `.\.venv\Scripts\python.exe -m ruff check .`, `.\.venv\Scripts\python.exe -m pytest -q`; full flow `tests\smoke\smoke_flow.py --stage <latest>` on the freshly seeded E2E stack (`start-all.ps1 -E2E`); Playwright `npx playwright test` only in P26.
- A failing smoke check means the code disagrees with `docs/04_API_CONTRACT.md`: fix the code. Change `tests/smoke/smoke_flow.py` only when it misreads docs/04, and record why in PROGRESS.
- Paste the exact command and its final summary line into `docs/PROGRESS.md`. Never claim a result you did not see.
- Never delete, skip (`@Disabled`, `.skip`, `xfail`), loosen or rewrite an assertion just to make it pass. If a test is wrong, explain why in the plan and get approval. The only allowed conditional skip: AI tests marked `@pytest.mark.models` skip when the model files are absent (CI only); at the P2/P6/P11 gates they must run.
- Every `db/tests/test_*.sql` file is one transaction ending in ROLLBACK, creates its own data (never relies on demo rows or identity values), prints `PASS …`/`FAIL …` NOTICEs and ends with `RAISE NOTICE '<NAME> TESTS PASSED: % / <total>'` — `scripts/ci/db-tests.sh` and `verify-all.ps1` check exactly that line.
- New endpoint ⇒ add its rows to the authorization matrix test. New error code ⇒ add it to `docs/12_ERROR_HANDLING.md` and test it. New migration ⇒ add a SQL test in `db/tests/` and a Testcontainers assertion.
- Tests must be deterministic: fixed seeds, fixed clock (`Clock` bean / freezegun), no real network (WireMock, MSW, fake OSRM matrices), Testcontainers, `civicbrain_test` (SQL + AI integration) or `civicbrain_e2e` (Playwright) only.
- After two failed attempts to fix the same failure, stop, summarise what you tried, and ask the human.
