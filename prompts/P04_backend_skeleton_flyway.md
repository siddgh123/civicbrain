# P04 — Backend skeleton, Flyway, demo seed
**Day 1–2 · agent ≈ 2 h · human ≈ 3 min (at the START) · Needs: P01 · Model: strongest**

## Goal
`backend/` builds with Spring Boot 4.1.1 / Java 25; Flyway builds the `civicbrain` database (V1–V5 + R__) on the
first start; the 500 synthetic demo complaints are loaded; one Testcontainers integration test proves the
schema; the error model, request id, security skeleton (deny-all) and configuration validation exist. No features.

## Human step (FIRST, ≈ 3 min)
1. Open this link in Chrome:
   `https://start.spring.io/#!type=maven-project&language=java&platformVersion=4.1.1&packaging=jar&jvmVersion=25&groupId=com.civicbrain&artifactId=civicbrain&name=civicbrain&description=CivicBrain%20API&packageName=com.civicbrain&dependencies=web,validation,data-jpa,security,oauth2-resource-server,flyway,postgresql,mail,thymeleaf,actuator`
2. Check: Maven, Java, Spring Boot **4.1.1** (if it is not offered, pick the newest 4.1.x without "SNAPSHOT"/"M"), Java **25**.
3. Click **GENERATE** → a zip downloads → extract its CONTENT into `C:\dev\civicbrain\backend\` (so `backend\pom.xml` and
   `backend\mvnw.cmd` exist). Say "done".
(The agent cannot download from start.spring.io itself - its browser is limited to localhost.)

## Read first
`.agents/rules/10-backend-spring.md` · `docs/02_ARCHITECTURE.md` §3, §6, §7 · `docs/03_DATABASE.md` §1, §3, §5 ·
`docs/09_BUILD_PLAN.md` P1 step 3 and P3 (dependency list) · `docs/12_ERROR_HANDLING.md` §1–§3 · `docs/07_SECURITY.md` §2, §4 ·
`.env.example` (property names)

## Build
1. `pom.xml`: parent `spring-boot-starter-parent` **4.1.1**, `java.version` 25, artifactId `civicbrain`. Keep the
   generated Boot-4 starters and add: `org.flywaydb:flyway-database-postgresql`, `org.hibernate.orm:hibernate-spatial`,
   test: `spring-boot-testcontainers`, Testcontainers PostgreSQL module (2.0.x, Boot-managed), `spring-security-test`.
   Non-Boot-managed libraries (add now, used from P06 on): `org.springdoc:springdoc-openapi-starter-webmvc-ui` 3.x,
   `com.bucket4j:bucket4j_jdk17-core` 8.x, `com.drewnoakes:metadata-extractor` 2.19.x, `com.github.librepdf:openpdf` 3.x,
   `org.bouncycastle:bcprov-jdk18on` (≥ 1.83), test `org.wiremock:wiremock-standalone` 3.x. Pick the newest release of
   each named line: `.\mvnw.cmd versions:display-dependency-updates` (without `-q`, which would hide the report; this is NOT an
   ASK-FIRST item); write the
   exact versions into the log. No Excel library (MVP OUT). JaCoCo plugin (report; the 70 % check is Phase 2).
   Failsafe plugin for `*IT` classes.
2. Copy (Copy-Item) `flyway\V1__…` … `V5__…` and `flyway\R__civicbrain_grants.sql` unchanged into
   `backend\src\main\resources\db\migration\` (the CI step "Migration copies are consistent" compares them).
3. `application.yml` (+ `application-dev.yml`, `-demo`, `-e2e`, `-e2e-seed`, `-bootstrap-admin` skeletons) with
   `${ENV}` placeholders from 02 §6 and rule 10 (Flyway user = PG_ADMIN_USER in every real-DB profile; datasource =
   civicbrain_app; `ddl-auto=validate`, `open-in-view=false`, fail-on-unknown-properties, actuator exposes `health` only (`management.health.mail.enabled=false` - SMTP problems must not make the app DOWN; the outbox retries),
   `server.error.include-*=never`, structured console logging). `src/test/resources/application-test.yml` with fake values.
4. `config`: `@ConfigurationProperties` records with `@Validated` (fail fast with the env-var name in the message),
   `Clock` bean, Jackson settings, `SecurityConfig` skeleton: deny-all; permit `/actuator/health`,
   `/api/v1/auth/**` (placeholder), `/api/v1/public/**`; stateless; security headers of 07 §4 (CSP, nosniff,
   frame-ancestors 'none', Referrer-Policy, Permissions-Policy camera/geolocation=self).
5. `common`: `ApiException(code, status, detail)`, `ErrorCode` enum (all codes of 12 §2), `@RestControllerAdvice`
   → RFC 9457 body with `code`, `requestId`, `fieldErrors`; SQLSTATE mapping of 12 §3 (P0001 prefixes, 23514
   "Invalid complaint status transition" → 409 INVALID_TRANSITION, 42501 → 403 ROLE_NOT_ALLOWED, 23505 → 409 ALREADY_EXISTS);
   `RequestIdFilter` (`X-Request-Id`, MDC); pagination record.
6. `workflow.WorkflowActor` (set_config of actor id/role/remarks in the same transaction) + a unit test that scans the
   sources for `setStatus(` outside `workflow` (02 §3).
7. Startup check: a `@Component` that, on `ApplicationReadyEvent` in `dev`/`demo`/`e2e`, runs `select count(*) from wards`
   as `civicbrain_app` and logs `DB check: <n> wards visible to civicbrain_app` (proves the R__ grants).

## Tests (write first)
- `SchemaIT` (Testcontainers `postgis/postgis:18-3.6`, `asCompatibleSubstituteFor("postgres")`, `@ServiceConnection`,
  one shared container): Flyway applies V1–V5 + R__ (R__ only logs a NOTICE without roles) · the 74 application
  tables of `db/SCHEMA_REFERENCE_after_V5.sql` exist · 23 wards · `fn_locate_point(18.7440, 73.6760)` → ward_number 1 ·
  inserting a user + complaint enqueues exactly one ANALYZE_COMPLAINT job.
- `ErrorAdviceTest`: validation error → 400 VALIDATION_FAILED with fieldErrors; unknown JSON field → 400; any exception
  → 500 INTERNAL_ERROR without stack trace, with requestId.
- `SecurityConfigTest`: an unknown `/api/v1/x` → 401; `/actuator/health` → 200; headers present.
- `ConfigValidationTest`: missing required property → startup fails naming it.

## Verify (agent)
1. in `backend`: `.\mvnw.cmd -q verify` (Docker Desktop must run - if not: human step "start Docker Desktop").
2. `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Only backend` → healthy; `logs\backend.log` shows Flyway
   "Successfully applied 6 migrations" (V1–V5 + R__) and `DB check: 23 wards visible to civicbrain_app`.
3. `pwsh -NoProfile -File scripts\dev\db-setup-main.ps1 -Seed` → "complaints=500, wards=23".
4. `pwsh -NoProfile -File scripts\dev\db-rebuild-test.ps1 -Force` still green (nothing changed in SQL).
5. Leave the backend running.

## Ask the human (yes/no)
- Q1. Open http://localhost:8080/actuator/health in Chrome - does it show `{"status":"UP"}`?
- Q2. (if GitHub is set up) Is the CI job "Backend (mvnw verify, Testcontainers, JaCoCo)" green for the latest push?

## Done when
verify green · Flyway built `civicbrain` · seed loaded · backend healthy · committed + pushed.

## Next
`/run-prompt P05` — frontend skeleton (≈ 1.5 h)
