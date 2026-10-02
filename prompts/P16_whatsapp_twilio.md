# P16 — WhatsApp channel (Twilio sandbox, or `log`)
**Day 5 (Mon 5 Oct) · agent ≈ 1.5 h · human ≈ 15 min · Needs: P10 · Model: any**
If Twilio is not possible (no account, no phone), answer "skip" in the human step: the channel stays `log` (every message is
written to the backend log as "would send") and the e-mails carry the demo (cut list item 3).

## Goal
Every citizen-facing status that has a WhatsApp template is sent through Twilio's WhatsApp sandbox to citizens who
opted in, through the same outbox as e-mail; a test message proves the credentials.

## Read first
`docs/02_ARCHITECTURE.md` §5 rules 5–10 · `docs/12_ERROR_HANDLING.md` §4 (timeouts/retries) · `docs/07_SECURITY.md` §5 ·
`.env.example` (TWILIO_*, WHATSAPP_PROVIDER) · the P10 `NotificationChannel` code

## Build
1. `TwilioWhatsAppChannel` (provider `TWILIO_SANDBOX`): `POST https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json`,
   HTTP Basic (SID:TOKEN), form fields `From=TWILIO_FROM` (`whatsapp:+14155238886`), `To=whatsapp:+91…`, `Body=<rendered text>`;
   MVP text + link only (no media; the INSPECTED/COMPLETED WhatsApp texts mention a photo - the photo is in the e-mail and the
   app; add this to the Known limitations in `docs/13_DEMO_AND_DEPLOY.md` §5); connect/read timeouts 5/10 s; 201 → SENT with the message `sid` as provider id; 4xx →
   FAILED without retry (bad number, not joined); 5xx/timeout → retry schedule of 02 §5 rule 10. Never log the token or the
   full phone (mask to +91******1234).
2. `LogWhatsAppChannel` stays (provider INTERNAL) and is used when `WHATSAPP_PROVIDER=log`.
3. Choose the channel by `WHATSAPP_PROVIDER`; WhatsApp rows only if `users.whatsapp_opt_in` and a phone exist (rule 5).
4. Profile `whatsapp-test` (non-web, schedulers off): sends ONE text "CivicBrain test message" to the number in
   `--to=+91…` through the configured provider and exits with the provider answer (status + sid, no secrets).
   Script `scripts/dev/send-test-whatsapp.ps1 -To +91XXXXXXXXXX` (loads `.env`, runs the jar with that profile; same style as
   `bootstrap-admin.ps1`; ASCII only). The human runs it.

## Tests (write first)
WireMock: 201 → SENT + sid stored; 400 → FAILED no retry; 500 → retry scheduled; request has Basic auth, From/To/Body fields
and the masked phone never appears in logs · opt-out user → no WhatsApp row · `log` provider writes one log line and SENT.

## Verify (agent)
in `backend`: `.\mvnw.cmd -q verify` · E2E smoke `--stage intake` still passes (provider `log` in E2E).

## Human step (≈ 15 min)
1. twilio.com → sign up (free trial) → Console → Messaging → Try it out → **Send a WhatsApp message** → note the sandbox
   number (+1 415 523 8886) and your join code.
2. From each test phone's WhatsApp, send `join <your-code>` to that number (the join lasts 72 h - repeat before the demo). Twilio also delivers free-form messages only within 24 h of that phone's LAST message to the sandbox number, so every
   test phone sends any message (e.g. "hi") to the sandbox within 24 h before P24 and again on demo morning
   (otherwise Twilio accepts the message - log shows SENT - but the phone never gets it, error 63016).
3. Open `C:\dev\civicbrain\.env` in Notepad and set: `WHATSAPP_PROVIDER=twilio`, `TWILIO_SID=<Account SID>`,
   `TWILIO_TOKEN=<Auth Token>`, `TWILIO_FROM=whatsapp:+14155238886`. Save. (The agent never opens `.env`.)
4. PowerShell 7: `pwsh -NoProfile -File scripts\dev\start-all.ps1 -Stop -Only backend` (the test script runs the jar itself and
   needs port 8080 free), then `pwsh -NoProfile -File scripts\dev\send-test-whatsapp.ps1 -To +91<your number>` → the phone gets the test message.
5. Say "done" - the agent restarts the backend (`start-all.ps1 -Only backend -Restart`).

## Ask the human (yes/no)
- Q1. Did the test WhatsApp message arrive on the phone?
- Q2. (optional now, required in P24) Make one status change happen for your own P13 complaint later - fine to check in P24?

## Done when
tests green · the test message arrived (or the human chose "skip" → `log` documented in PROGRESS) · committed + pushed.

## Next
`/run-prompt P17` — planning engine (≈ 2.5 h, strongest model)
