"""CivicBrain | tests/smoke/smoke_flow.py - end-to-end API smoke test (the agent's own full-flow check)

Talks to a RUNNING stack through the public API exactly as docs/04_API_CONTRACT.md defines it, reads the
fixed E2E accounts from .env.test itself (like Playwright does) and reads OTP mails from Mailpit.
It never prints passwords, tokens, OTP codes or TOTP secrets.

Run it against the E2E stack (fresh data every time):
    pwsh -NoProfile -File scripts\\dev\\start-all.ps1 -Stop
    pwsh -NoProfile -File scripts\\dev\\seed-e2e.ps1
    pwsh -NoProfile -File scripts\\dev\\start-all.ps1 -E2E
    ai-service\\.venv\\Scripts\\python.exe tests\\smoke\\smoke_flow.py --stage <stage>
    pwsh -NoProfile -File scripts\\dev\\start-all.ps1 -Restart          # back to the dev stack

Stages (each one first runs all stages before it, in one go; 'auth' is independent):
    auth        P06  fresh citizen: register -> OTP (Mailpit) -> verify -> login -> /me -> refresh rotation/reuse -> logout
    intake      P10  citizen1 complaint A + validation errors + other citizen 404 + SUBMITTED e-mail
    analysis    P12  A becomes VERIFIED; citizen2's B 40 m away (similar text) becomes MERGED into A; C 445 m away VERIFIED
    officer     P14  officer queue/detail, reject + restore C, out-of-scope officer 404, invalid move 409
    plan        P18  generate -> reorder (RETIME) -> approve -> wrong contractor 422 -> assign -> e-mails -> PDF
    contractor  P20  worklist, other firm 404, inspection -> start -> completion with proof photo, officer e-mail
    close       P23  verify -> CLOSED, rating, "not fixed" -> REOPENED, rejected completion -> REOPENED -> plannable again
    all         = close

Exit code: 0 all checks passed, 1 a check failed, 2 precondition (stack down, E2E data not fresh, stage not built yet).
A failing check means the CODE disagrees with docs/04 (fix the code); only fix this file if it misreads docs/04,
and record that in docs/PROGRESS.md.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import hmac
import io
import json
import random
import re
import secrets
import struct
import sys
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[2]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STAGES = ["intake", "analysis", "officer", "plan", "contractor", "close"]
REF_RE = re.compile(r"^CB-\d{6}$")
COOKIE = "__Host-cb_rt"


class CheckFailed(Exception):
    pass


class Precondition(Exception):
    pass


# ---------------------------------------------------------------- environment
def read_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines, # comments, optional quotes - same rules as scripts/dev/_common.ps1 Import-DotEnv."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, sep, val = line.partition("=")
        if not sep:
            continue
        val = val.strip()
        m = re.match(r"""^(["'])(.*?)\1(\s+#.*)?$""", val)
        if m:
            val = m.group(2)
        elif " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        out[key.strip()] = val
    return out


def totp(secret_b32: str, at: float | None = None, step: int = 30, digits: int = 6) -> str:
    """RFC 6238 (SHA-1) - same as authenticator apps."""
    key = base64.b32decode(secret_b32.upper() + "=" * (-len(secret_b32) % 8))
    counter = int((time.time() if at is None else at) // step)
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    off = mac[-1] & 0x0F
    code = (struct.unpack(">I", mac[off : off + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(code).zfill(digits)


def make_jpeg(seed: int, size: tuple[int, int] = (1280, 960)) -> bytes:
    """A unique photo-like JPEG WITH an EXIF block (camera make/model), so the server's EXIF stripping is tested
    and SHA-256/pHash reuse checks are not triggered between complaints."""
    from PIL import Image, ImageDraw

    rnd = random.Random(seed)
    img = Image.new("RGB", size, (rnd.randint(60, 120), rnd.randint(60, 120), rnd.randint(60, 120)))
    d = ImageDraw.Draw(img)
    for _ in range(40):
        x, y = rnd.randint(0, size[0]), rnd.randint(0, size[1])
        w, h = rnd.randint(20, 400), rnd.randint(20, 300)
        d.ellipse([x, y, x + w, y + h], fill=(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)))
    exif = Image.Exif()
    exif[0x010F] = "SmokeCam"  # Make
    exif[0x0110] = "CivicBrain smoke"  # Model
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88, exif=exif.tobytes())
    return buf.getvalue()


def point(env: dict[str, str], key: str, default: str) -> tuple[float, float]:
    lat, lon = (float(x) for x in env.get(key, default).split(","))
    return lat, lon


# ---------------------------------------------------------------- context / results
class Ctx:
    def __init__(self, args: argparse.Namespace):
        self.env = read_env_file(REPO / ".env.test")
        self.api = (args.api or self.env.get("E2E_API_URL", "http://127.0.0.1:8080")).rstrip("/") + "/api/v1"
        self.mailpit = (args.mailpit or self.env.get("E2E_MAILPIT_URL", "http://127.0.0.1:8025")).rstrip("/")
        self.origin = self.env.get("E2E_BASE_URL", "http://localhost:5173").rstrip("/")
        self.http = httpx.Client(timeout=30.0, follow_redirects=False)
        self.passed = 0
        self.failed = 0
        self.ai_timeout = args.ai_timeout
        self.seed = secrets.randbits(32)
        self.photo_n = 0

    # every check prints one line; a failure stops the current stage (later steps depend on it)
    def check(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed += 1
            print(f"PASS  {name}")
        else:
            self.failed += 1
            print(f"FAIL  {name}" + (f": {detail}" if detail else ""))
            raise CheckFailed(name)

    def account(self, prefix: str) -> tuple[str, str]:
        email, pw = self.env.get(f"E2E_{prefix}_EMAIL"), self.env.get(f"E2E_{prefix}_PASSWORD")
        if not email or not pw or pw.startswith("REPLACE_ME"):
            raise Precondition(f".env.test has no usable E2E_{prefix}_EMAIL/PASSWORD (scripts\\dev\\new-env.ps1 fills them)")
        return email, pw

    def photo(self) -> tuple[str, bytes]:
        self.photo_n += 1
        return f"photo{self.photo_n}.jpg", make_jpeg(self.seed + self.photo_n)


def code_of(r: httpx.Response) -> str:
    """The problem 'code' of a JSON object body; "" for a JSON array (e.g. docs/04 sec. 3 /public/categories) or non-JSON."""
    try:
        body = r.json()
    except ValueError:
        return ""
    return str(body.get("code", "")) if isinstance(body, dict) else ""


def brief(r: httpx.Response) -> str:
    return f"HTTP {r.status_code} code={code_of(r) or '-'}"


class Session:
    """A logged-in user: bearer token + the refresh cookie handled by hand (Secure cookie over http://127.0.0.1)."""

    def __init__(self, ctx: Ctx, email: str, token: str, cookie: str | None):
        self.ctx, self.email, self.token, self.cookie = ctx, email, token, cookie

    def req(self, method: str, path: str, **kw) -> httpx.Response:
        headers = kw.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        return self.ctx.http.request(method, self.ctx.api + path, headers=headers, **kw)

    def get(self, path: str, **kw) -> httpx.Response:
        return self.req("GET", path, **kw)

    def post(self, path: str, **kw) -> httpx.Response:
        return self.req("POST", path, **kw)

    def put(self, path: str, **kw) -> httpx.Response:
        return self.req("PUT", path, **kw)


def refresh_cookie(r: httpx.Response) -> str | None:
    for h in r.headers.get_list("set-cookie"):
        if h.startswith(COOKIE + "="):
            return h.split(";", 1)[0].split("=", 1)[1] or None
    return None


# ---------------------------------------------------------------- mailpit
def _mail_list(ctx: Ctx, to_addr: str) -> list[dict]:
    try:
        r = ctx.http.get(ctx.mailpit + "/api/v1/search", params={"query": f'to:"{to_addr}"', "limit": 100})
        return r.json().get("messages", []) if r.status_code == 200 else []
    except (httpx.HTTPError, ValueError):
        return []


def mail_ids(ctx: Ctx, to_addr: str) -> set[str]:
    """IDs of the messages already in Mailpit for to_addr - call BEFORE the action whose mail you expect
    (no clock comparison: the Mailpit container clock may drift from the laptop clock)."""
    return {m["ID"] for m in _mail_list(ctx, to_addr)}


def mail_text(ctx: Ctx, to_addr: str, must_contain: list[str], seen: set[str], timeout: float = 60.0) -> str | None:
    """Text of a NEW message (ID not in `seen`) to to_addr that contains every string in must_contain.
    Uses the plain-text part when present (HTML only as a fallback, without <style>/<script> blocks)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for m in _mail_list(ctx, to_addr):
            if m["ID"] in seen:
                continue
            full = ctx.http.get(f"{ctx.mailpit}/api/v1/message/{m['ID']}").json()
            body = full.get("Text") or ""
            if not body.strip():
                html = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", full.get("HTML") or "")
                body = re.sub(r"<[^>]+>", " ", html)
            text = (full.get("Subject") or "") + "\n" + body
            if all(x.lower() in text.lower() for x in must_contain):
                return text
        time.sleep(2)
    return None


# ---------------------------------------------------------------- auth helpers
def login(ctx: Ctx, email: str, password: str, totp_key: str | None = None) -> Session:
    r = ctx.http.post(ctx.api + "/auth/login", json={"identifier": email, "password": password})
    ctx.check(f"login {email.split('@')[0]}", r.status_code == 200, brief(r))
    body = r.json()
    if body.get("mfaRequired"):
        secret = ctx.env.get(totp_key or "")
        if not secret:
            raise Precondition(f"{email} needs TOTP but .env.test has no {totp_key}")
        r = ctx.http.post(ctx.api + "/auth/mfa/verify", json={"mfaToken": body["mfaToken"], "code": totp(secret)})
        ctx.check(f"TOTP login {email.split('@')[0]}", r.status_code == 200, brief(r))
        body = r.json()
    if body.get("mfaSetupRequired"):
        raise Precondition(f"{email}: TOTP setup required - the E2E seed must enable TOTP for officers when TOTP is on")
    ctx.check(f"access token for {email.split('@')[0]}", bool(body.get("accessToken")), "no accessToken in body")
    return Session(ctx, email, body["accessToken"], refresh_cookie(r))


def register_fresh(ctx: Ctx) -> tuple[str, str]:
    tag = secrets.token_hex(4)
    email = f"smoke-{tag}@smoke.local"
    password = "Smoke-" + secrets.token_urlsafe(12)
    phone = "+919" + "".join(str(random.randint(0, 9)) for _ in range(9))
    r = ctx.http.get(ctx.api + "/public/privacy-notice")
    ctx.check("GET /public/privacy-notice has a version", r.status_code == 200 and bool(r.json().get("version")), brief(r))
    notice_version = r.json()["version"]
    seen = mail_ids(ctx, email)
    r = ctx.http.post(
        ctx.api + "/auth/register",
        json={
            "fullName": f"Smoke Test {tag}",
            "email": email,
            "phone": phone,
            "password": password,
            "privacyNoticeVersion": notice_version,
            "consents": {"whatsapp": False, "publicPhoto": False, "aiTraining": False},
        },
    )
    ctx.check("register -> 202 with otpId", r.status_code == 202 and bool(r.json().get("otpId")), brief(r))
    otp_id = r.json()["otpId"]
    text = mail_text(ctx, email, [], seen, timeout=45)
    ctx.check("OTP e-mail arrived in Mailpit", text is not None, "no mail within 45 s (Mailpit running? SMTP 1025?)")
    m = re.search(r"\b(\d{6})\b", text or "")
    ctx.check("OTP e-mail contains a 6-digit code", m is not None)
    r = ctx.http.post(ctx.api + "/auth/verify-otp", json={"otpId": otp_id, "code": "000000" if m.group(1) != "000000" else "111111"})
    ctx.check("wrong OTP -> 422 OTP_INVALID", r.status_code == 422 and code_of(r) == "OTP_INVALID", brief(r))
    r = ctx.http.post(ctx.api + "/auth/verify-otp", json={"otpId": otp_id, "code": m.group(1)})
    ctx.check("verify-otp -> 200", r.status_code == 200, brief(r))
    return email, password


# ---------------------------------------------------------------- complaint helpers
def categories(ctx: Ctx) -> dict[str, dict]:
    r = ctx.http.get(ctx.api + "/public/categories")
    ctx.check("GET /public/categories", r.status_code == 200 and isinstance(r.json(), list), brief(r))
    return {c["name"]: c for c in r.json()}


def new_capture(sess: Session, path: str = "/citizen/capture-sessions") -> str:
    r = sess.post(path)
    sess.ctx.check(f"capture session ({path.split('/')[1]})", r.status_code == 201 and bool(r.json().get("captureSessionId")), brief(r))
    return r.json()["captureSessionId"]


def complaint_data(cat: dict, lat: float, lon: float, session_id: str, title: str, desc: str, **over) -> dict:
    data = {
        "categoryId": cat["id"],
        "title": title,
        "description": desc,
        "landmark": "Smoke test",
        "latitude": lat,
        "longitude": lon,
        "locationAccuracyM": 12,
        "locationCapturedAt": dt.datetime.now(IST).isoformat(timespec="seconds"),
        "devicePitchDeg": 55.0,
        "deviceRollDeg": 1.0,
        "captureSessionId": session_id,
        "captureMethod": "IN_APP_CAMERA",
        "a4InFrame": False,
    }
    if cat.get("needsDepthAnswer"):
        data["depthAnswer"] = "FINGER"
    data.update(over)
    return {k: v for k, v in data.items() if v is not None}


def post_complaint(sess: Session, data: dict, photo: tuple[str, bytes], mime: str = "image/jpeg") -> httpx.Response:
    files = [("data", ("data.json", json.dumps(data).encode(), "application/json")), ("photo", (photo[0], photo[1], mime))]
    return sess.post("/citizen/complaints", files=files)


def submit(sess: Session, cat: dict, lat: float, lon: float, title: str, desc: str) -> dict:
    sid = new_capture(sess)
    r = post_complaint(sess, complaint_data(cat, lat, lon, sid, title, desc), sess.ctx.photo())
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    sess.ctx.check(
        f"complaint '{title}' -> 201 with publicRef", r.status_code == 201 and bool(REF_RE.match(str(body.get("publicRef", "")))), brief(r)
    )
    body["captureSessionId"] = sid
    return body


def citizen_detail(sess: Session, cid: int) -> dict:
    r = sess.get(f"/citizen/complaints/{cid}")
    sess.ctx.check(f"citizen detail {cid}", r.status_code == 200, brief(r))
    return r.json()


def wait_status(sess: Session, cid: int, wanted: set[str], timeout: float) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        r = sess.get(f"/citizen/complaints/{cid}")
        if r.status_code == 200:
            last = r.json()
            if last.get("status") in wanted:
                return last
        time.sleep(2)
    return last


def officer_action(sess: Session, cid: int, action: str, body: dict) -> httpx.Response:
    return sess.post(f"/officer/complaints/{cid}/{action}", json=body)


def wait_run(sess: Session, run_id, timeout: float = 90.0) -> dict:
    deadline = time.time() + timeout
    body = {}
    while time.time() < deadline:
        r = sess.get(f"/officer/optimizer-runs/{run_id}")
        if r.status_code == 200:
            body = r.json()
            if body.get("status") in ("SUCCEEDED", "FAILED"):
                return body
        time.sleep(2)
    return body


def find_id_by_email(items: list[dict], email: str):
    for it in items:
        blob = json.dumps(it).lower()
        if email.lower() in blob:
            return it.get("id") or it.get("contractorId")
    return None


# ---------------------------------------------------------------- stages
def stage_auth(ctx: Ctx, st: dict) -> None:
    email, pw = register_fresh(ctx)
    s = login(ctx, email, pw)
    ctx.check("login sets the refresh cookie", s.cookie is not None, f"no {COOKIE} Set-Cookie header")
    r = s.get("/me")
    ctx.check(
        "GET /me -> CITIZEN, own e-mail",
        r.status_code == 200 and r.json().get("role") == "CITIZEN" and r.json().get("email", "").lower() == email,
        brief(r),
    )
    r = ctx.http.get(ctx.api + "/me")
    ctx.check("GET /me without token -> 401", r.status_code == 401, brief(r))
    bad = ctx.http.post(ctx.api + "/auth/login", json={"identifier": email, "password": pw + "x"})
    unknown = ctx.http.post(ctx.api + "/auth/login", json={"identifier": f"nobody-{secrets.token_hex(3)}@smoke.local", "password": pw})
    ctx.check(
        "wrong password and unknown account -> same 401 INVALID_CREDENTIALS",
        bad.status_code == unknown.status_code == 401 and code_of(bad) == code_of(unknown) == "INVALID_CREDENTIALS",
        f"{brief(bad)} / {brief(unknown)}",
    )
    hdr = {"X-CB-CSRF": "1", "Origin": ctx.origin}
    r = ctx.http.post(ctx.api + "/auth/refresh", headers={**hdr, "Cookie": f"{COOKIE}={s.cookie}"})
    new_cookie = refresh_cookie(r)
    ctx.check(
        "refresh -> 200 + rotated cookie",
        r.status_code == 200 and bool(r.json().get("accessToken")) and new_cookie is not None and new_cookie != s.cookie,
        brief(r),
    )
    r = ctx.http.post(ctx.api + "/auth/refresh", headers={"Origin": ctx.origin, "Cookie": f"{COOKIE}={new_cookie}"})
    ctx.check("refresh without X-CB-CSRF -> 403 CSRF_CHECK_FAILED", r.status_code == 403 and code_of(r) == "CSRF_CHECK_FAILED", brief(r))
    r = ctx.http.post(ctx.api + "/auth/refresh", headers={**hdr, "Cookie": f"{COOKIE}={s.cookie}"})
    ctx.check("reuse of the rotated cookie -> 401", r.status_code == 401, brief(r))
    r = ctx.http.post(ctx.api + "/auth/refresh", headers={**hdr, "Cookie": f"{COOKIE}={new_cookie}"})
    ctx.check("after reuse the whole family is revoked -> 401", r.status_code == 401, brief(r))
    s2 = login(ctx, email, pw)
    r = ctx.http.post(ctx.api + "/auth/logout", headers={**hdr, "Cookie": f"{COOKIE}={s2.cookie}"})
    ctx.check("logout -> 204", r.status_code == 204, brief(r))


def stage_intake(ctx: Ctx, st: dict) -> None:
    c1_email, c1_pw = ctx.account("CITIZEN1")
    c2_email, c2_pw = ctx.account("CITIZEN2")
    c1 = login(ctx, c1_email, c1_pw)
    c2 = login(ctx, c2_email, c2_pw)
    r = c1.get("/citizen/complaints")
    ctx.check("citizen1 list works", r.status_code == 200, brief(r))
    if r.json().get("totalItems", 0) != 0:
        raise Precondition("citizen1 already has complaints - the E2E data is not fresh: run scripts\\dev\\seed-e2e.ps1 first")
    cats = categories(ctx)
    for name in ("Pothole", "Road Damage", "Garbage Accumulation", "Waterlogging"):
        ctx.check(f"category {name} exists", name in cats)
    pin = point(ctx.env, "E2E_POINT_IN", "18.7440,73.6760")
    pout = point(ctx.env, "E2E_POINT_OUT", "18.7700,73.7500")
    pothole = cats["Pothole"]
    seen_c1 = mail_ids(ctx, c1_email)
    a = submit(c1, pothole, *pin, "Deep pothole near the temple", "Large pothole on the road near the temple, vehicles are slipping.")
    ctx.check(
        "A: status SUBMITTED, ward 1",
        a.get("status") == "SUBMITTED" and a.get("wardNumber") == 1,
        json.dumps({k: a.get(k) for k in ("status", "wardNumber")}),
    )
    # validation errors (docs/04 sec. 5 order; docs/12 codes)
    r = post_complaint(c1, complaint_data(pothole, *pin, a["captureSessionId"], "Again", "Reused capture session test."), ctx.photo())
    ctx.check(
        "used capture session -> 422 CAPTURE_SESSION_INVALID", r.status_code == 422 and code_of(r) == "CAPTURE_SESSION_INVALID", brief(r)
    )
    r = post_complaint(
        c1, complaint_data(pothole, *pin, new_capture(c1), "Far fix", "Accuracy test text.", locationAccuracyM=400), ctx.photo()
    )
    ctx.check("accuracy 400 m -> 422 GPS_ACCURACY_TOO_LOW", r.status_code == 422 and code_of(r) == "GPS_ACCURACY_TOO_LOW", brief(r))
    r = post_complaint(c1, complaint_data(pothole, *pout, new_capture(c1), "Outside", "Outside boundary test."), ctx.photo())
    ctx.check("outside TDMC -> 422 OUTSIDE_BOUNDARY", r.status_code == 422 and code_of(r) == "OUTSIDE_BOUNDARY", brief(r))
    r = post_complaint(
        c1,
        complaint_data(pothole, *pin, new_capture(c1), "Text file", "Wrong file type test."),
        ("photo.jpg", b"this is not an image, just text " * 40),
    )
    ctx.check("text file as photo -> 415 FILE_TYPE_NOT_ALLOWED", r.status_code == 415 and code_of(r) == "FILE_TYPE_NOT_ALLOWED", brief(r))
    r = post_complaint(
        c1, complaint_data(pothole, *pin, new_capture(c1), "No depth", "Depth answer missing test.", depthAnswer=None), ctx.photo()
    )
    ctx.check("Pothole without depthAnswer -> 400 VALIDATION_FAILED", r.status_code == 400 and code_of(r) == "VALIDATION_FAILED", brief(r))
    d = citizen_detail(c1, a["complaintId"])
    ctx.check(
        "A detail: timeline + images",
        isinstance(d.get("timeline"), list) and len(d["timeline"]) >= 1 and isinstance(d.get("images"), list) and len(d["images"]) >= 1,
    )
    r = c2.get(f"/citizen/complaints/{a['complaintId']}")
    ctx.check("citizen2 opens citizen1's complaint -> 404", r.status_code == 404 and code_of(r) == "NOT_FOUND", brief(r))
    r = c2.get(f"/files/{d['images'][0]['imageId']}")
    ctx.check("citizen2 downloads citizen1's photo -> 404", r.status_code == 404, brief(r))
    r = c1.get(f"/files/{d['images'][0]['imageId']}")
    ctx.check("citizen1 downloads own photo (JPEG)", r.status_code == 200 and r.content[:2] == b"\xff\xd8", brief(r))
    ctx.check("stored photo has no EXIF", b"Exif" not in r.content[:4096])
    text = mail_text(ctx, c1_email, [a["publicRef"]], seen_c1, timeout=60)
    ctx.check("SUBMITTED e-mail to citizen1 mentions the CB number", text is not None, "no mail within 60 s (outbox dispatcher?)")
    st.update(c1=c1, c2=c2, cats=cats, a=a, pin=pin, c1_email=c1_email, c2_email=c2_email)


def stage_analysis(ctx: Ctx, st: dict) -> None:
    c1, c2, a = st["c1"], st["c2"], st["a"]
    d = wait_status(c1, a["complaintId"], {"VERIFIED", "MERGED"}, ctx.ai_timeout)
    ctx.check(
        f"A analysed by the worker -> VERIFIED within {ctx.ai_timeout:.0f} s",
        d.get("status") == "VERIFIED",
        f"status={d.get('status')} (worker running on the E2E database? logs\\worker.log)",
    )
    near = point(ctx.env, "E2E_POINT_NEAR", "18.7442,73.6763")
    b = submit(c2, st["cats"]["Pothole"], *near, "Pothole near temple", "Big pothole on the road close to the temple, bikes are slipping.")
    db = wait_status(c2, b["complaintId"], {"VERIFIED", "MERGED"}, ctx.ai_timeout)
    ctx.check("B (40 m, similar text) -> MERGED", db.get("status") == "MERGED", f"status={db.get('status')}")
    ctx.check(
        "B shows 'Linked to' A's CB number",
        db.get("mergedIntoPublicRef") == a["publicRef"],
        f"mergedIntoPublicRef={db.get('mergedIntoPublicRef')}",
    )
    far = point(ctx.env, "E2E_POINT_FAR", "18.7400,73.6760")
    c = submit(c1, st["cats"]["Road Damage"], *far, "Broken road surface by the school", "Road surface cracked and broken for 3 metres.")
    dc = wait_status(c1, c["complaintId"], {"VERIFIED", "MERGED"}, ctx.ai_timeout)
    ctx.check("C (445 m away, other text) -> VERIFIED", dc.get("status") == "VERIFIED", f"status={dc.get('status')}")
    st.update(b=b, c=c, far=far)


def stage_officer(ctx: Ctx, st: dict) -> None:
    oe, op = ctx.account("OFFICER_ROAD")
    off = login(ctx, oe, op, "E2E_OFFICER_ROAD_TOTP_SECRET")
    a, c = st["a"], st["c"]
    r = off.get("/officer/complaints", params={"tab": "NEW", "size": 100})
    ids = [i.get("complaintId", i.get("id")) for i in r.json().get("items", [])] if r.status_code == 200 else []
    ctx.check("officer NEW tab lists A and C", r.status_code == 200 and a["complaintId"] in ids and c["complaintId"] in ids, brief(r))
    ctx.check("merged child B is not listed on its own", st["b"]["complaintId"] not in ids)
    r = off.get(f"/officer/complaints/{a['complaintId']}")
    ctx.check("officer detail of A", r.status_code == 200 and r.json().get("publicRef") == a["publicRef"], brief(r))
    r = off.get("/officer/complaints/geojson", params={"tab": "NEW"})
    ctx.check("officer geojson", r.status_code == 200 and r.json().get("type") == "FeatureCollection", brief(r))
    r = officer_action(off, c["complaintId"], "reject", {"reason": "Smoke test reject"})
    ctx.check("reject C -> 200", r.status_code == 200, brief(r))
    ctx.check("citizen sees C REJECTED", citizen_detail(st["c1"], c["complaintId"]).get("status") == "REJECTED")
    r = officer_action(off, c["complaintId"], "restore", {"reason": "Smoke test restore"})
    ctx.check(
        "restore C -> 200, VERIFIED again",
        r.status_code == 200 and citizen_detail(st["c1"], c["complaintId"]).get("status") == "VERIFIED",
        brief(r),
    )
    r = officer_action(off, a["complaintId"], "verify-completion", {"approved": True, "remarks": "too early"})
    ctx.check(
        "verify-completion on a VERIFIED complaint -> 409 INVALID_TRANSITION",
        r.status_code == 409 and code_of(r) == "INVALID_TRANSITION",
        brief(r),
    )
    we, wp = ctx.account("OFFICER_W3")
    w3 = login(ctx, we, wp, "E2E_OFFICER_W3_TOTP_SECRET")
    r = w3.get(f"/officer/complaints/{a['complaintId']}")
    ctx.check("ward-3 officer opens a ward-1 complaint -> 404", r.status_code == 404, brief(r))
    r = st["c1"].get("/officer/complaints", params={"tab": "NEW"})
    ctx.check("citizen calls an officer endpoint -> 403", r.status_code == 403, brief(r))
    st.update(off=off, officer_email=oe)


def stage_plan(ctx: Ctx, st: dict) -> None:
    off, a, c = st["off"], st["a"], st["c"]
    planned = (dt.datetime.now(IST) + dt.timedelta(days=1)).date().isoformat()
    r = off.post(
        "/officer/plans/generate",
        json={"plannedDate": planned, "workTypeCode": "ROAD", "complaintIds": [a["complaintId"], c["complaintId"]]},
    )
    ctx.check("generate plan -> 202 runId", r.status_code == 202 and r.json().get("runId") is not None, brief(r))
    run = wait_run(off, r.json()["runId"])
    ctx.check(
        "optimizer run SUCCEEDED with one plan",
        run.get("status") == "SUCCEEDED" and len(run.get("actionPlanIds") or []) == 1,
        json.dumps({k: run.get(k) for k in ("status", "error", "droppedJobs")})[:300],
    )
    pid = run["actionPlanIds"][0]
    plan = off.get(f"/officer/plans/{pid}").json()
    items = sorted(plan.get("items", []), key=lambda i: i["sequenceNo"])
    ctx.check(
        "DRAFT plan with A and C",
        plan.get("status") == "DRAFT" and {i["complaintId"] for i in items} == {a["complaintId"], c["complaintId"]},
    )
    swapped = [{"complaintId": it["complaintId"], "sequenceNo": n} for n, it in enumerate(reversed(items), start=1)]
    r = off.put(f"/officer/plans/{pid}", json={"version": plan["version"], "plannedDate": planned, "items": swapped, "notes": "smoke"})
    ctx.check("reorder (PUT) -> 202 runId", r.status_code == 202, brief(r))
    run2 = wait_run(off, r.json()["runId"])
    plan2 = off.get(f"/officer/plans/{pid}").json()
    order2 = [i["complaintId"] for i in sorted(plan2.get("items", []), key=lambda i: i["sequenceNo"])]
    ctx.check(
        "RETIME kept the officer's order, version +1",
        run2.get("status") == "SUCCEEDED" and order2 == [s["complaintId"] for s in swapped] and plan2.get("version") == plan["version"] + 1,
        f"run={run2.get('status')} order={order2}",
    )
    r = off.put(f"/officer/plans/{pid}", json={"version": plan["version"], "plannedDate": planned, "items": swapped, "notes": "stale"})
    ctx.check("edit with an old version -> 409 STALE_VERSION", r.status_code == 409 and code_of(r) == "STALE_VERSION", brief(r))
    r = off.post(f"/officer/plans/{pid}/approve")
    ctx.check(
        "approve -> APPROVED, complaints SCHEDULED",
        r.status_code in (200, 204) and citizen_detail(st["c1"], a["complaintId"]).get("status") == "SCHEDULED",
        brief(r),
    )
    # the firms are looked up as ADMIN (an officer's list may be limited to the officer's work types)
    ae, ap = ctx.account("ADMIN")
    adm = login(ctx, ae, ap, "E2E_ADMIN_TOTP_SECRET")
    r = adm.get("/officer/contractors", params={"size": 100})
    body = r.json() if r.status_code == 200 else []
    lst = body.get("items", []) if isinstance(body, dict) else body
    ce, _ = ctx.account("CONTRACTOR")
    oe2, _ = ctx.account("CONTRACTOR_OTHER")
    good, other = find_id_by_email(lst, ce), find_id_by_email(lst, oe2)
    ctx.check("contractor list shows both E2E firms (by e-mail)", good is not None and other is not None, brief(r))
    r = off.post(f"/officer/plans/{pid}/assign", json={"contractorId": other})
    ctx.check(
        "assign a WATER firm to a ROAD plan -> 422 CONTRACTOR_NOT_ELIGIBLE",
        r.status_code == 422 and code_of(r) == "CONTRACTOR_NOT_ELIGIBLE",
        brief(r),
    )
    seen = {addr: mail_ids(ctx, addr) for addr in (st["c1_email"], st["c2_email"], ce)}
    r = off.post(f"/officer/plans/{pid}/assign", json={"contractorId": good})
    ctx.check("assign -> 200", r.status_code in (200, 204), brief(r))
    da = citizen_detail(st["c1"], a["complaintId"])
    ctx.check(
        "citizen sees ASSIGNED + contractor name + planned date",
        da.get("status") == "ASSIGNED" and bool(da.get("contractorName")) and bool(da.get("plannedDate")),
        json.dumps({k: da.get(k) for k in ("status", "plannedDate")}),
    )
    ctx.check(
        "e-mail to citizen1: A assigned, contractor named",
        mail_text(ctx, st["c1_email"], [a["publicRef"], da["contractorName"]], seen[st["c1_email"]]) is not None,
    )
    ctx.check(
        "e-mail to citizen2 (merged child B's owner) about the master",
        mail_text(ctx, st["c2_email"], [da["contractorName"]], seen[st["c2_email"]]) is not None,
    )
    ctx.check("ACTION_PLAN_ASSIGNED e-mail to the contractor", mail_text(ctx, ce, [plan["planCode"]], seen[ce]) is not None)
    r = off.get(f"/officer/plans/{pid}/export.pdf")
    ctx.check(
        "plan PDF download",
        r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf") and r.content[:4] == b"%PDF",
        brief(r),
    )
    st.update(pid=pid, planned=planned, plan_code=plan["planCode"], contractor_email=ce)


def stage_contractor(ctx: Ctx, st: dict) -> None:
    ce, cp = ctx.account("CONTRACTOR")
    con = login(ctx, ce, cp)
    a, c = st["a"], st["c"]
    r = con.get("/contractor/worklist", params={"date": st["planned"]})
    ctx.check(
        "contractor worklist contains A and C",
        r.status_code == 200 and str(a["publicRef"]) in r.text and str(c["publicRef"]) in r.text,
        brief(r),
    )
    xe, xp = ctx.account("CONTRACTOR_OTHER")
    other = login(ctx, xe, xp)
    r = other.get(f"/contractor/complaints/{a['complaintId']}")
    ctx.check("other firm opens A -> 404", r.status_code == 404, brief(r))
    r = con.get(f"/contractor/complaints/{a['complaintId']}")
    ctx.check("contractor detail has no citizen e-mail/phone", r.status_code == 200 and st["c1_email"] not in r.text.lower(), brief(r))
    seen_off = mail_ids(ctx, st["officer_email"])
    for cmp, (lat, lon) in ((a, st["pin"]), (c, st["far"])):
        sid = new_capture(con, "/contractor/capture-sessions")
        data = {
            "issueConfirmed": True,
            "findings": "Confirmed on site (smoke)",
            "lengthM": 0.6,
            "widthM": 0.4,
            "depthM": 0.05,
            "expectedCompletionDate": st["planned"],
            "latitude": lat,
            "longitude": lon,
            "accuracyM": 10,
            "captureSessionId": sid,
        }
        files = [("data", ("data.json", json.dumps(data).encode(), "application/json")), ("photos", (*ctx.photo(), "image/jpeg"))]
        r = con.post(f"/contractor/complaints/{cmp['complaintId']}/inspection", files=files)
        ctx.check(f"inspection {cmp['publicRef']} -> 201", r.status_code == 201, brief(r))
        r = con.post(f"/contractor/complaints/{cmp['complaintId']}/start")
        ctx.check(f"start {cmp['publicRef']} -> 200", r.status_code == 200, brief(r))
        sid = new_capture(con, "/contractor/capture-sessions")
        data = {
            "workSummary": "Repaired (smoke)",
            "actualWorkers": 3,
            "actualHours": 2.5,
            "materialsUsed": [],
            "latitude": lat,
            "longitude": lon,
            "accuracyM": 10,
            "captureSessionId": sid,
        }
        files = [("data", ("data.json", json.dumps(data).encode(), "application/json")), ("photos", (*ctx.photo(), "image/jpeg"))]
        r = con.post(f"/contractor/complaints/{cmp['complaintId']}/completion", files=files)
        ctx.check(f"completion {cmp['publicRef']} -> 201", r.status_code == 201, brief(r))
    ctx.check("citizen sees A COMPLETED", citizen_detail(st["c1"], a["complaintId"]).get("status") == "COMPLETED")
    ctx.check("COMPLETION_SUBMITTED e-mail to the officer", mail_text(ctx, st["officer_email"], [a["publicRef"]], seen_off) is not None)
    r = st["off"].get(f"/officer/plans/{st['pid']}")
    ctx.check(
        "plan COMPLETED when every item is done",
        r.status_code == 200 and r.json().get("status") == "COMPLETED",
        f"plan status={r.json().get('status') if r.status_code == 200 else brief(r)}",
    )


def stage_close(ctx: Ctx, st: dict) -> None:
    off, c1, a, c = st["off"], st["c1"], st["a"], st["c"]
    r = officer_action(off, a["complaintId"], "verify-completion", {"approved": True, "remarks": "Checked photos (smoke)"})
    ctx.check("verify A -> CLOSED", r.status_code == 200 and citizen_detail(c1, a["complaintId"]).get("status") == "CLOSED", brief(r))
    r = c1.post(f"/citizen/complaints/{a['complaintId']}/feedback", json={"isResolved": True, "rating": 4, "comment": "ok"})
    ctx.check("citizen rates A (4 stars) -> 201", r.status_code == 201, brief(r))
    r = officer_action(off, c["complaintId"], "verify-completion", {"approved": False, "remarks": "Proof unclear (smoke)"})
    ctx.check(
        "reject C's completion -> REOPENED",
        r.status_code == 200 and citizen_detail(c1, c["complaintId"]).get("status") == "REOPENED",
        brief(r),
    )
    planned = (dt.datetime.now(IST) + dt.timedelta(days=2)).date().isoformat()
    r = off.post("/officer/plans/generate", json={"plannedDate": planned, "workTypeCode": "ROAD", "complaintIds": [c["complaintId"]]})
    run = wait_run(off, r.json().get("runId")) if r.status_code == 202 else {}
    ctx.check(
        "REOPENED C is plannable again (new DRAFT plan)",
        run.get("status") == "SUCCEEDED" and len(run.get("actionPlanIds") or []) == 1,
        brief(r),
    )
    r = c1.post(f"/citizen/complaints/{a['complaintId']}/feedback", json={"isResolved": False, "comment": "Pothole is back"})
    ctx.check(
        "citizen says 'Not fixed' on CLOSED A -> REOPENED",
        r.status_code == 201 and citizen_detail(c1, a["complaintId"]).get("status") == "REOPENED",
        brief(r),
    )
    r = st["c2"].post(f"/citizen/complaints/{st['b']['complaintId']}/feedback", json={"isResolved": True})
    ctx.check(
        "feedback on a MERGED complaint -> 422 FEEDBACK_NOT_ALLOWED",
        r.status_code == 422 and code_of(r) == "FEEDBACK_NOT_ALLOWED",
        brief(r),
    )


STAGE_FUNCS = {
    "intake": stage_intake,
    "analysis": stage_analysis,
    "officer": stage_officer,
    "plan": stage_plan,
    "contractor": stage_contractor,
    "close": stage_close,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", required=True, choices=["auth", *STAGES, "all"])
    ap.add_argument("--api", help="default E2E_API_URL from .env.test (http://127.0.0.1:8080)")
    ap.add_argument("--mailpit", help="default E2E_MAILPIT_URL from .env.test (http://127.0.0.1:8025)")
    ap.add_argument("--ai-timeout", type=float, default=90.0, help="seconds to wait for the worker per complaint")
    args = ap.parse_args(argv)
    ctx = Ctx(args)
    try:
        r = ctx.http.get(ctx.api.rsplit("/api/v1", 1)[0] + "/actuator/health")
        if r.status_code != 200:
            raise Precondition(f"backend health {r.status_code}")
    except (httpx.HTTPError, Precondition) as e:
        print(f"PRECONDITION  backend not reachable at {ctx.api} ({e}) - start-all.ps1 -E2E")
        return 2
    try:
        ctx.http.get(ctx.mailpit + "/api/v1/info").raise_for_status()
    except httpx.HTTPError:
        print("PRECONDITION  Mailpit not reachable (start-all.ps1 starts it)")
        return 2

    todo = ["auth"] if args.stage == "auth" else STAGES[: (len(STAGES) if args.stage == "all" else STAGES.index(args.stage) + 1)]
    state: dict = {}
    current = ""
    try:
        for name in todo:
            current = name
            print(f"==> stage {name}")
            (stage_auth if name == "auth" else STAGE_FUNCS[name])(ctx, state)
    except Precondition as e:
        print(f"PRECONDITION  {e}")
        return 2
    except CheckFailed:
        print(f"SMOKE {args.stage.upper()} FAILED in stage '{current}': {ctx.passed} passed, {ctx.failed} failed")
        return 1
    except (httpx.HTTPError, KeyError, ValueError, TypeError, AttributeError, IndexError) as e:
        print(f"FAIL  stage '{current}' crashed: {type(e).__name__}: {e}")
        print(f"SMOKE {args.stage.upper()} FAILED in stage '{current}': {ctx.passed} passed, {ctx.failed + 1} failed")
        return 1
    print(f"SMOKE {args.stage.upper()} PASSED: {ctx.passed} / {ctx.passed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
