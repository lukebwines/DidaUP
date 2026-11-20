"""DidaUP 0.1 alpha: accounts, academic years, scoped cohort exclusions.

No administrative source data is bundled with this application.
Do not use with actual University data until environment and safeguards are approved.
"""
from __future__ import annotations

import hashlib
import tempfile
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .source_import import MAX_UPLOAD_BYTES, check_signature, inspect_workbook

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DIDAUP_DATA_DIR", "/data"))
DB = DATA / "didaup.sqlite3"
SOURCE_DIR = DATA / "sources"
CONFIG_FILE = Path(os.environ.get("DIDAUP_OPTIONS_PATH", "/data/options.json"))
COOKIE_NAME = "didaup_session"
SESSION_SECONDS = 12 * 60 * 60
HASH_ITERATIONS = 390_000
USERNAME_RE = re.compile(r"[a-zA-Z0-9._-]{3,40}\Z")
ACADEMIC_RE = re.compile(r"(20\d{2})/(\d{2})\Z")
COURSE_RE = re.compile(r"[a-zA-Z0-9._-]{1,40}\Z")
settings: dict = {}

app = FastAPI(title="DidaUP", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


def options() -> dict:
    if CONFIG_FILE.is_file():
        with CONFIG_FILE.open(encoding="utf-8") as file:
            cfg = json.load(file)
            if not isinstance(cfg, dict):
                raise RuntimeError("Configurazione DidaUP non valida")
            return cfg
    return {
        "bootstrap_username": os.environ.get("DIDAUP_BOOTSTRAP_USERNAME", "admin"),
        "bootstrap_password": os.environ.get("DIDAUP_BOOTSTRAP_PASSWORD", ""),
        "secure_cookies": os.environ.get("DIDAUP_SECURE_COOKIES", "true").lower() == "true",
    }


def connect() -> sqlite3.Connection:
    cx = sqlite3.connect(DB, timeout=15)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys=ON")
    cx.execute("PRAGMA busy_timeout=15000")
    return cx


def password_hash(value: str) -> str:
    salt = secrets.token_bytes(16)
    result = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${salt.hex()}${result.hex()}"


def verify_password(value: str, encoded: str) -> bool:
    try:
        method, iterations, salt, target = encoded.split("$")
        if method != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual, bytes.fromhex(target))
    except (ValueError, TypeError):
        return False


def check_password(value: str):
    if not 12 <= len(value) <= 128:
        raise HTTPException(422, "La password deve avere tra 12 e 128 caratteri")


def check_aa(value: str):
    match = ACADEMIC_RE.fullmatch(value)
    if not match or int(match[2]) != (int(match[1]) + 1) % 100:
        raise HTTPException(422, "Formato anno accademico non valido: es. 2026/27")


def record(cx: sqlite3.Connection, actor: int | None, action: str, entity: str, record_id: int | None):
    cx.execute(
        "INSERT INTO audit(at,actor_id,action,entity,record_id) VALUES(?,?,?,?,?)",
        (int(time.time()), actor, action, entity, record_id),
    )


@app.on_event("startup")
def startup():
    global settings
    settings = options()
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    # The persistent /data directory is prepared by the add-on entrypoint.
    os.chmod(DATA, 0o700)
    with closing(connect()) as cx:
        cx.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(
              id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
              passhash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','operatore','lettura')),
              active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1,
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions(
              token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
              csrf TEXT NOT NULL, expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS login_attempts(
              attempt_key TEXT PRIMARY KEY, started_at INTEGER NOT NULL, failures INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recovery_operations(
              id INTEGER PRIMARY KEY CHECK(id=1), credential_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS academic_years(
              id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, status TEXT NOT NULL,
              created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cohorts(
              id INTEGER PRIMARY KEY,
              year_id INTEGER NOT NULL REFERENCES academic_years(id),
              course_code TEXT NOT NULL, course_name TEXT NOT NULL, campus TEXT NOT NULL,
              study_year INTEGER NOT NULL CHECK(study_year BETWEEN 1 AND 12),
              included INTEGER NOT NULL DEFAULT 1,
              exclusion_reason TEXT NOT NULL DEFAULT '',
              version INTEGER NOT NULL DEFAULT 1,
              UNIQUE(year_id, course_code, campus, study_year)
            );
            CREATE TABLE IF NOT EXISTS source_imports(
              id INTEGER PRIMARY KEY,
              year_id INTEGER NOT NULL REFERENCES academic_years(id),
              kind TEXT NOT NULL CHECK(kind IN ('offerta','docenti')),
              original_name TEXT NOT NULL, stored_name TEXT NOT NULL UNIQUE,
              sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL,
              sheets_json TEXT NOT NULL,
              status TEXT NOT NULL, created_at INTEGER NOT NULL,
              actor_id INTEGER NOT NULL REFERENCES users(id),
              UNIQUE(year_id,kind,sha256)
            );
            CREATE TABLE IF NOT EXISTS audit(
              id INTEGER PRIMARY KEY, at INTEGER NOT NULL, actor_id INTEGER,
              action TEXT NOT NULL, entity TEXT NOT NULL, record_id INTEGER
            );
            """
        )
        n = cx.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if n == 0:
            username = str(settings.get("bootstrap_username", "admin")).strip()
            password = str(settings.get("bootstrap_password") or "")
            if not USERNAME_RE.fullmatch(username):
                raise RuntimeError("Configurare bootstrap_username con 3-40 caratteri validi")
            if len(password) < 12 or len(password) > 128:
                raise RuntimeError("Prima installazione: impostare bootstrap_password di almeno 12 caratteri")
            cx.execute(
                "INSERT INTO users(username,passhash,role,created_at) VALUES(?,?,?,?)",
                (username, password_hash(password), "admin", int(time.time())),
            )
        # Emergency reset is activated only from Home Assistant add-on options.
        # A salted hash of the last used recovery password prevents reapplying the
        # same recovery after future restarts (including after in-app changes).
        recovery_password = str(settings.get("admin_recovery_password") or "")
        if recovery_password:
            if not 12 <= len(recovery_password) <= 128:
                raise RuntimeError("admin_recovery_password deve avere tra 12 e 128 caratteri")
            previous = cx.execute(
                "SELECT credential_hash FROM recovery_operations WHERE id=1"
            ).fetchone()
            if previous is None or not verify_password(recovery_password, previous["credential_hash"]):
                admin_login = str(settings.get("bootstrap_username", "admin")).strip()
                admin = cx.execute(
                    "SELECT id FROM users WHERE username=? COLLATE NOCASE",
                    (admin_login,),
                ).fetchone()
                if admin is None:
                    raise RuntimeError(
                        "Recupero admin impossibile: l'utente bootstrap non esiste. "
                        "Non cancellare il database."
                    )
                cx.execute(
                    """UPDATE users SET passhash=?,active=1,role='admin',version=version+1
                       WHERE id=?""",
                    (password_hash(recovery_password), admin["id"]),
                )
                cx.execute("DELETE FROM sessions WHERE user_id=?", (admin["id"],))
                cx.execute("DELETE FROM login_attempts")
                cx.execute(
                    "INSERT OR REPLACE INTO recovery_operations(id,credential_hash) VALUES(1,?)",
                    (password_hash(recovery_password),),
                )
                record(cx, admin["id"], "recover_admin", "user", admin["id"])
        cx.execute(
            "INSERT OR IGNORE INTO academic_years(code,status,created_at) VALUES(?,?,?)",
            ("2026/27", "storico_in_preparazione", int(time.time())),
        )
        cx.execute("DELETE FROM sessions WHERE expires_at < ?", (int(time.time()),))
        cx.commit()
    try:
        os.chmod(DB, 0o600)
    except OSError:
        pass


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; form-action 'self'; "
        "frame-ancestors 'self'; base-uri 'none'"
    )
    return response


@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/healthz")
def health():
    return {"status": "ok"}


def cookie_path(request: Request) -> str:
    """Scope ingress sessions to the add-on subpath, not all Home Assistant URLs."""
    ingress = request.headers.get("x-ingress-path", "")
    if ingress and re.fullmatch(r"/api/hassio_ingress/[A-Za-z0-9_-]+/?", ingress):
        return ingress.rstrip("/") + "/"
    return "/"


def current_user(request: Request, allowed: tuple[str, ...] = ("admin", "operatore", "lettura")) -> dict:
    token = request.cookies.get(COOKIE_NAME, "")
    if len(token) < 30:
        raise HTTPException(401, "Accesso richiesto")
    key = hashlib.sha256(token.encode()).hexdigest()
    with closing(connect()) as cx:
        row = cx.execute(
            """SELECT u.id,u.username,u.role,u.active,u.version,s.csrf,s.expires_at
            FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?""", (key,)
        ).fetchone()
    if row is None or not row["active"] or row["expires_at"] <= time.time():
        raise HTTPException(401, "Sessione scaduta o non valida")
    if row["role"] not in allowed:
        raise HTTPException(403, "Permessi insufficienti")
    return dict(row)


def require_write(request: Request, user: dict, allow_multipart: bool = False):
    site = request.headers.get("sec-fetch-site")
    if site == "cross-site":
        raise HTTPException(403, "Richiesta da origine non autorizzata")
    content_type = request.headers.get("content-type", "").split(";")[0].strip()
    allowed = ("application/json", "multipart/form-data") if allow_multipart else ("application/json",)
    if content_type not in allowed:
        raise HTTPException(415, "Tipo contenuto non consentito")
    incoming = request.headers.get("x-csrf-token", "")
    if not incoming or not hmac.compare_digest(incoming, user["csrf"]):
        raise HTTPException(403, "Token CSRF non valido")


class Login(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=128)


@app.post("/api/login")
def login(body: Login, request: Request):
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Origine non autorizzata")
    name = body.username.strip()
    source_ip = str(request.client.host if request.client else "unknown")
    attempt_key = hashlib.sha256((name.casefold() + "|" + source_ip).encode()).hexdigest()
    now = int(time.time())
    with closing(connect()) as cx:
        attempt = cx.execute("SELECT * FROM login_attempts WHERE attempt_key=?", (attempt_key,)).fetchone()
        if attempt and now - attempt["started_at"] < 900 and attempt["failures"] >= 6:
            raise HTTPException(429, "Troppi tentativi. Riprovare più tardi")
        user = cx.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (name,)).fetchone()
        if user is None or not user["active"] or not verify_password(body.password, user["passhash"]):
            if not attempt or now - attempt["started_at"] >= 900:
                cx.execute("INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)", (attempt_key, now, 1))
            else:
                cx.execute("UPDATE login_attempts SET failures=failures+1 WHERE attempt_key=?", (attempt_key,))
            cx.commit()
            raise HTTPException(401, "Credenziali non valide")
        cx.execute("DELETE FROM login_attempts WHERE attempt_key=?", (attempt_key,))
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        cx.execute("INSERT INTO sessions VALUES (?,?,?,?)",
                   (hashlib.sha256(token.encode()).hexdigest(), user["id"], csrf, now + SESSION_SECONDS))
        record(cx, user["id"], "login", "session", None)
        cx.commit()
    from fastapi.responses import JSONResponse
    response = JSONResponse({"ok": True})
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, secure=bool(settings.get("secure_cookies", True)),
        samesite="lax", max_age=SESSION_SECONDS, path=cookie_path(request),
    )
    return response


@app.get("/api/session")
def session(request: Request):
    user = current_user(request)
    return {"id": user["id"], "username": user["username"], "role": user["role"],
            "csrf": user["csrf"]}


@app.post("/api/logout")
def logout(request: Request):
    user = current_user(request)
    require_write(request, user)
    token = request.cookies.get(COOKIE_NAME, "")
    with closing(connect()) as cx:
        cx.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
        record(cx, user["id"], "logout", "session", None)
        cx.commit()
    from fastapi.responses import JSONResponse
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME, path=cookie_path(request))
    return response


@app.get("/api/years")
def years(request: Request):
    current_user(request)
    with closing(connect()) as cx:
        rows = cx.execute(
            """SELECT a.id,a.code,a.status,a.created_at,
              (SELECT COUNT(*) FROM cohorts c WHERE c.year_id=a.id) AS total,
              (SELECT COUNT(*) FROM cohorts c WHERE c.year_id=a.id AND c.included=0) AS excluded
              FROM academic_years a ORDER BY a.code DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


class NewYear(BaseModel):
    code: str = Field(max_length=7)


@app.post("/api/years")
def add_year(body: NewYear, request: Request):
    user = current_user(request, ("admin", "operatore"))
    require_write(request, user)
    check_aa(body.code)
    with closing(connect()) as cx:
        try:
            cur = cx.execute(
                "INSERT INTO academic_years(code,status,created_at) VALUES(?,?,?)",
                (body.code, "in_preparazione", int(time.time())),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Anno accademico già presente")
        record(cx, user["id"], "create", "academic_year", cur.lastrowid)
        cx.commit()
    return {"id": cur.lastrowid, "code": body.code, "status": "in_preparazione"}


def ensure_year(cx: sqlite3.Connection, year_id: int):
    row = cx.execute("SELECT id FROM academic_years WHERE id=?", (year_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Anno accademico inesistente")


@app.get("/api/years/{year_id}/cohorts")
def list_cohorts(year_id: int, request: Request):
    current_user(request)
    with closing(connect()) as cx:
        ensure_year(cx, year_id)
        rows = cx.execute(
            """SELECT id,course_code,course_name,campus,study_year,included,
                      exclusion_reason,version FROM cohorts WHERE year_id=?
               ORDER BY course_name,campus,study_year""", (year_id,)
        ).fetchall()
    return [dict(r) for r in rows]


class NewCohort(BaseModel):
    course_code: str = Field(min_length=1, max_length=40)
    course_name: str = Field(min_length=2, max_length=120)
    campus: str = Field(min_length=1, max_length=80)
    study_year: int = Field(ge=1, le=12)


@app.post("/api/years/{year_id}/cohorts")
def add_cohort(year_id: int, body: NewCohort, request: Request):
    user = current_user(request, ("admin", "operatore"))
    require_write(request, user)
    code = body.course_code.strip()
    if not COURSE_RE.fullmatch(code):
        raise HTTPException(422, "Codice CdS non valido")
    name = body.course_name.strip()
    campus = body.campus.strip()
    if len(name) < 2 or not campus:
        raise HTTPException(422, "CdS e sede obbligatori")
    with closing(connect()) as cx:
        ensure_year(cx, year_id)
        try:
            cur = cx.execute(
                """INSERT INTO cohorts(year_id,course_code,course_name,campus,study_year)
                   VALUES(?,?,?,?,?)""",
                (year_id, code, name, campus, body.study_year),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Annualità già presente per questo CdS e sede")
        record(cx, user["id"], "create", "cohort", cur.lastrowid)
        cx.commit()
    return {"id": cur.lastrowid, "included": True, "version": 1}


class CohortDecision(BaseModel):
    included: bool
    reason: str = Field(default="", max_length=500)
    expected_version: int = Field(ge=1)


@app.patch("/api/cohorts/{cohort_id}")
def set_cohort(cohort_id: int, body: CohortDecision, request: Request):
    user = current_user(request, ("admin", "operatore"))
    require_write(request, user)
    reason = body.reason.strip()
    if not body.included and len(reason) < 3:
        raise HTTPException(422, "Motivazione obbligatoria per escludere un'annualità")
    with closing(connect()) as cx:
        row = cx.execute("SELECT * FROM cohorts WHERE id=?", (cohort_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Annualità inesistente")
        result = cx.execute(
            """UPDATE cohorts SET included=?,exclusion_reason=?,version=version+1
               WHERE id=? AND version=?""",
            (int(body.included), "" if body.included else reason, cohort_id, body.expected_version),
        )
        if result.rowcount != 1:
            raise HTTPException(409, "Il dato è stato modificato da un altro operatore: ricaricare")
        record(cx, user["id"], "include" if body.included else "exclude", "cohort", cohort_id)
        cx.commit()
    return {"id": cohort_id, "included": body.included, "version": body.expected_version + 1}


@app.get("/api/users")
def list_users(request: Request):
    current_user(request, ("admin",))
    with closing(connect()) as cx:
        rows = cx.execute(
            "SELECT id,username,role,active,version,created_at FROM users ORDER BY username"
        ).fetchall()
    return [dict(r) for r in rows]


class NewUser(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "operatore", "lettura"] = "operatore"


@app.post("/api/users")
def add_user(body: NewUser, request: Request):
    user = current_user(request, ("admin",))
    require_write(request, user)
    username = body.username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "Nome utente non valido")
    check_password(body.password)
    with closing(connect()) as cx:
        try:
            cur = cx.execute(
                "INSERT INTO users(username,passhash,role,created_at) VALUES(?,?,?,?)",
                (username, password_hash(body.password), body.role, int(time.time())),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Account già esistente")
        record(cx, user["id"], "create", "user", cur.lastrowid)
        cx.commit()
    return {"id": cur.lastrowid, "username": username, "role": body.role}


class UserChange(BaseModel):
    role: Literal["admin", "operatore", "lettura"]
    active: bool
    expected_version: int = Field(ge=1)
    new_password: str | None = Field(default=None, max_length=128)


@app.patch("/api/users/{user_id}")
def edit_user(user_id: int, body: UserChange, request: Request):
    actor = current_user(request, ("admin",))
    require_write(request, actor)
    if body.new_password is not None:
        check_password(body.new_password)
    with closing(connect()) as cx:
        target = cx.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if target is None:
            raise HTTPException(404, "Utente inesistente")
        if user_id == actor["id"] and (not body.active or body.role != "admin"):
            raise HTTPException(409, "Non puoi revocare il tuo ruolo amministratore")
        new_hash = password_hash(body.new_password) if body.new_password is not None else target["passhash"]
        changed = cx.execute(
            """UPDATE users SET role=?,active=?,passhash=?,version=version+1
               WHERE id=? AND version=?""",
            (body.role, int(body.active), new_hash, user_id, body.expected_version),
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Modifica concorrente: ricaricare gli account")
        if not body.active or body.new_password is not None or target["role"] != body.role:
            cx.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        record(cx, actor["id"], "update", "user", user_id)
        cx.commit()
    return {"id": user_id, "version": body.expected_version + 1}


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


@app.post("/api/account/password")
def change_password(body: ChangePassword, request: Request):
    actor = current_user(request)
    require_write(request, actor)
    check_password(body.new_password)
    with closing(connect()) as cx:
        row = cx.execute("SELECT passhash FROM users WHERE id=?", (actor["id"],)).fetchone()
        if row is None or not verify_password(body.current_password, row["passhash"]):
            raise HTTPException(403, "Password corrente non valida")
        cx.execute("UPDATE users SET passhash=?,version=version+1 WHERE id=?",
                   (password_hash(body.new_password), actor["id"]))
        token = request.cookies.get(COOKIE_NAME, "")
        current_token_hash = hashlib.sha256(token.encode()).hexdigest()
        cx.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (actor["id"], current_token_hash))
        record(cx, actor["id"], "change_password", "user", actor["id"])
        cx.commit()
    return {"ok": True}


@app.get("/api/audit")
def list_audit(request: Request):
    current_user(request, ("admin",))
    with closing(connect()) as cx:
        rows = cx.execute(
            """SELECT at,actor_id,action,entity,record_id FROM audit
               ORDER BY id DESC LIMIT 100"""
        ).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/years/{year_id}/imports")
def list_imports(year_id: int, request: Request):
    current_user(request)
    with closing(connect()) as cx:
        ensure_year(cx, year_id)
        rows = cx.execute(
            """SELECT id,kind,original_name,sha256,size_bytes,sheets_json,status,created_at
               FROM source_imports WHERE year_id=? ORDER BY id DESC""",
            (year_id,),
        ).fetchall()
    return [{**dict(row), "sheets": json.loads(row["sheets_json"])} for row in rows]


@app.post("/api/years/{year_id}/imports")
async def upload_source(
    year_id: int, request: Request,
    kind: str = Form(...), source: UploadFile = File(...),
    test_data_only: bool = Form(False),
):
    actor = current_user(request, ("admin", "operatore"))
    require_write(request, actor, allow_multipart=True)
    if kind not in ("offerta", "docenti"):
        raise HTTPException(422, "Tipologia di report non valida")
    if not test_data_only:
        raise HTTPException(422, "Collaudo consentito solo con dati sintetici")
    original_name = Path((source.filename or "").replace("\\", "/")).name
    suffix = Path(original_name).suffix.lower()
    if suffix not in (".xls", ".xlsx") or len(original_name) > 180:
        raise HTTPException(422, "Sono ammessi soltanto file Excel .xls e .xlsx")
    with closing(connect()) as cx:
        ensure_year(cx, year_id)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, file_path = tempfile.mkstemp(prefix="source_", suffix=suffix, dir=SOURCE_DIR)
    stored = Path(file_path)
    size = 0
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as output:
            while True:
                chunk = await source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "File troppo grande: massimo 32 MB")
                digest.update(chunk)
                output.write(chunk)
        if not size:
            raise HTTPException(422, "File vuoto")
        try:
            check_signature(stored, suffix)
            sheets = await run_in_threadpool(inspect_workbook, stored)
        except Exception as exc:
            raise HTTPException(422, "Excel non leggibile o non supportato") from exc

        with closing(connect()) as cx:
            ensure_year(cx, year_id)
            previous = cx.execute(
                "SELECT id FROM source_imports WHERE year_id=? AND kind=? AND sha256=?",
                (year_id, kind, digest.hexdigest()),
            ).fetchone()
            if previous is not None:
                raise HTTPException(409, "Questo stesso report è già stato acquisito per l'anno selezionato")
            cursor = cx.execute(
                """INSERT INTO source_imports(
                   year_id,kind,original_name,stored_name,sha256,size_bytes,
                   sheets_json,status,created_at,actor_id) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (year_id, kind, original_name, stored.name, digest.hexdigest(), size,
                 json.dumps(sheets, ensure_ascii=False), "acquisito_da_mappare",
                 int(time.time()), actor["id"]),
            )
            record(cx, actor["id"], "import_source", "source_import", cursor.lastrowid)
            cx.commit()
        os.chmod(stored, 0o600)
        return {
            "id": cursor.lastrowid, "kind": kind, "size_bytes": size,
            "status": "acquisito_da_mappare", "sheets": sheets,
        }
    except Exception:
        stored.unlink(missing_ok=True)
        raise
    finally:
        await source.close()

@app.get("/api/admin/archive/summary")
def archive_summary(request: Request):
    current_user(request, ("admin",))
    with closing(connect()) as cx:
        years = cx.execute(
            """SELECT a.id,a.code,
               (SELECT COUNT(*) FROM cohorts c WHERE c.year_id=a.id) cohorts,
               (SELECT COUNT(*) FROM source_imports s WHERE s.year_id=a.id) imports
               FROM academic_years a ORDER BY code DESC"""
        ).fetchall()
    return [dict(year) for year in years]


class ArchiveReset(BaseModel):
    scope: Literal["year", "all"]
    year_id: int | None = None
    confirmation: str = Field(max_length=80)
    password: str = Field(min_length=1, max_length=128)


@app.post("/api/admin/archive/reset")
def reset_archive(body: ArchiveReset, request: Request):
    actor = current_user(request, ("admin",))
    require_write(request, actor)
    with closing(connect()) as cx:
        stored_user = cx.execute("SELECT passhash FROM users WHERE id=?", (actor["id"],)).fetchone()
        if stored_user is None or not verify_password(body.password, stored_user["passhash"]):
            raise HTTPException(403, "Password amministratore non corretta")
        if body.scope == "year":
            if body.year_id is None:
                raise HTTPException(422, "Selezionare un anno accademico")
            row = cx.execute("SELECT code FROM academic_years WHERE id=?", (body.year_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "Anno accademico inesistente")
            if body.confirmation != "AZZERA " + row["code"]:
                raise HTTPException(422, "Conferma testuale non valida")
            sources = cx.execute(
                "SELECT stored_name FROM source_imports WHERE year_id=?", (body.year_id,)
            ).fetchall()
            cx.execute("DELETE FROM cohorts WHERE year_id=?", (body.year_id,))
            cx.execute("DELETE FROM source_imports WHERE year_id=?", (body.year_id,))
            record(cx, actor["id"], "reset_year", "academic_year", body.year_id)
        else:
            if body.confirmation != "AZZERA ARCHIVIO":
                raise HTTPException(422, "Conferma testuale non valida")
            sources = cx.execute("SELECT stored_name FROM source_imports").fetchall()
            cx.execute("DELETE FROM cohorts")
            cx.execute("DELETE FROM source_imports")
            cx.execute("DELETE FROM academic_years")
            cx.execute(
                "INSERT INTO academic_years(code,status,created_at) VALUES(?,?,?)",
                ("2026/27", "storico_in_preparazione", int(time.time())),
            )
            record(cx, actor["id"], "reset_all", "academic_year", None)
        cx.commit()
    failures = 0
    for src in sources:
        try:
            (SOURCE_DIR / src["stored_name"]).unlink(missing_ok=True)
        except OSError:
            failures += 1
    if failures:
        raise HTTPException(
            500,
            f"Archivio azzerato ma {failures} file locali richiedono la rimozione manuale",
        )
    return {"ok": True, "scope": body.scope, "deleted_files": len(sources)}
