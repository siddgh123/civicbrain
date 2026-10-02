# KIT_FIXES — CivicBrain_Kit_ClaudeCode me lagaye gaye 5 bug fixes (2 Oct 2026)

Ye `CivicBrain_Kit_ClaudeCode.zip` hi hai, bas neeche wali 11 files badli hain, aur `prompts/P00_orientation.md` me
setup checks + "Known and accepted" decisions add kiye hain (taaki P00 pehle se tay baaton ko blocker na bole). Baaki sab byte-for-byte same hai
(`.claude/settings.json` ke 379 deny rules, `CLAUDE.md`, `sync-claude.ps1` sab unchanged).
`sync-claude.ps1 -Check` = PASS (10 files current).

| # | File(s) | Fix | Kyun |
|---|---|---|---|
| 1 | `scripts/dev/start-all.ps1` | `-Only` me comma list (`worker,ai-api`) ab chalti hai | `pwsh -File ... -Only worker,ai-api` (P02, P08, P09, AGENTS.md) pehle hamesha "does not belong to the set" error deta tha |
| 2 | `scripts/dev/start-all.ps1`, `scripts/dev/start-tunnel.ps1` | Tunnel URL regex `api.trycloudflare.com` ko reject karta hai | Tunnel fail hone par error line ka URL "PHONE URL" ban jaata tha |
| 3 | `.agents/rules/10-backend-spring.md` (+ uski generated copy `.claude/rules/10-backend-spring.md`), `prompts/P06_auth_backend.md`, `scripts/dev/bootstrap-admin.ps1` | MVP me admin pe TOTP force nahi hoga (sirf `mfa-required=true` / P25 ke baad) | P06 `mfa-required=false` rakhta hai aur TOTP screens sirf optional P25 me hain. Forced TOTP hota to P24 me admin login hi nahi kar paata |
| 4 | `prompts/P08_classify_detect_authenticity.md` | Verify: YOLO + text classifier loaded; MiniLM P09 me aata hai | P08 apne hi verify step me fail hota |
| 5 | `prompts/P16_whatsapp_twilio.md`, `prompts/P24_full_flow_phones.md`, `docs/10_SETUP_WINDOWS.md`, `docs/09_BUILD_PLAN_7DAY.md` | Twilio ka 24-ghante wala rule | Message tabhi deliver hota hai jab phone ne pichhle 24 h me sandbox ko message bheja ho, warna log me SENT dikhta hai par phone pe kuch nahi aata (error 63016) |

Test kiya: saare `scripts/dev/*.ps1` PowerShell 7 parser se 0 errors; `-Only worker,ai-api` sahi bind hota hai;
`sync-claude.ps1 -Check` PASS.
