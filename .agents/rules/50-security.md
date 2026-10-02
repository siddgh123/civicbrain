---
trigger: model_decision
description: Apply when working on authentication, authorization, sessions, tokens, OTP/TOTP, passwords, file uploads, personal data, privacy/consent, security headers, logging of user data, rate limits, webhooks or secrets.
---

# Security checklist for this task

Read `docs/07_SECURITY.md` fully before planning. Then confirm in the plan how the change satisfies each relevant item:
1. Deny by default; the endpoint is in the SecurityFilterChain for the right role and in the authorization matrix test with every role × ownership case.
2. Object-level check is inside the query; not-owned = 404.
3. DTO exposes only fields this role may see (no citizen phone/e-mail to contractors, no internal scores to citizens).
4. Input validated (sizes, ranges, enums, unknown fields rejected); files by magic bytes, size, pixel limits, re-encoded, stored with random names outside the web root.
5. Passwords Argon2id; OTP HMAC + expiry + attempts; TOTP replay blocked; tokens never logged; refresh cookie `__Host-cb_rt` rotated with reuse detection; `token_valid_after` enforced.
6. Rate limit added where the endpoint can be abused (login, OTP, register, uploads, complaint creation).
7. Audit log entry for every state change; no secrets/PII in logs (mask phones).
8. Privacy: consent respected (WhatsApp opt-in, public photo, AI training); public outputs anonymised.
9. Webhooks verify signatures in constant time.
10. Tests prove the negative cases (wrong role, other user's object, expired/replayed tokens, bad file, rate limit).
