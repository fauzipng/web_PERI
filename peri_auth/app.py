"""API autentikasi PERI (Flask + SQLite).

Jalankan (dari folder peri-auth):  python app.py   -> http://127.0.0.1:5001

Aturan peran:
  - Register lewat web lembaga  -> role 'pendaftar' (otomatis, tidak bisa memilih role).
  - Role 'admin'                -> hanya dari database (lihat buat_admin.py / README di pesan).
"""
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import sqlite3
import time
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path

from flask import Flask, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("PERI_DB", BASE / "peri.db"))
KEY_PATH = BASE / "secret.key"

KODE_BERLAKU = 10 * 60      # detik
KODE_JEDA_KIRIM = 60        # detik antar permintaan kode
KODE_MAKS_COBA = 5
LOGIN_MAKS_GAGAL = 5
LOGIN_KUNCI = 5 * 60        # detik

KATEGORI_BUKU_TAMU = {"saran", "kritik", "pertanyaan", "kerjasama", "lainnya"}
KIRIM_MAKS = 10             # pesan per IP
KIRIM_JENDELA = 10 * 60     # detik

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ORIGIN_RE = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")
EXTRA_ORIGINS = {o.strip() for o in os.environ.get("PERI_ORIGINS", "").split(",") if o.strip()}


def _secret_key() -> bytes:
    """Kunci penanda cookie sesi; dibuat sekali lalu disimpan di secret.key."""
    if not KEY_PATH.exists():
        KEY_PATH.write_bytes(secrets.token_bytes(32))
    return KEY_PATH.read_bytes()


app = Flask(__name__)
app.secret_key = _secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("PERI_HTTPS") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)


# ---------------------------------------------------------------- database
def db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def tutup_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'pendaftar'
                          CHECK (role IN ('pendaftar', 'admin')),
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS buku_tamu (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nama      TEXT NOT NULL,
            email     TEXT NOT NULL,
            kategori  TEXT NOT NULL,
            pesan     TEXT NOT NULL,
            dibaca    INTEGER NOT NULL DEFAULT 0,
            dibuat    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS kode_verifikasi (
            email       TEXT PRIMARY KEY COLLATE NOCASE,
            kode_hash   TEXT NOT NULL,
            kedaluwarsa REAL NOT NULL,
            percobaan   INTEGER NOT NULL DEFAULT 0,
            dikirim     REAL NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


# -------------------------------------------------------------------- CORS
@app.after_request
def cors(resp):
    origin = request.headers.get("Origin", "")
    if origin and (ORIGIN_RE.match(origin) or origin in EXTRA_ORIGINS):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Vary"] = "Origin"
    return resp


@app.route("/api/<path:_p>", methods=["OPTIONS"])
def preflight(_p):
    return "", 204


# ----------------------------------------------------------------- helpers
def galat(pesan, kode=400):
    return jsonify(error=pesan), kode


def json_body():
    return request.get_json(silent=True) or {}


def norm_email(v):
    return v.strip().lower() if isinstance(v, str) else ""


def hash_kode(email, kode):
    return hmac.new(app.secret_key, f"{email}:{kode}".encode(), hashlib.sha256).hexdigest()


def user_publik(row):
    return {"email": row["email"], "role": row["role"]}


def user_saat_ini():
    """Pengguna dari sesi. Role selalu dibaca ulang dari database."""
    uid = session.get("uid")
    if not uid:
        return None
    return db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def kirim_email(tujuan, kode):
    host = os.environ.get("PERI_SMTP_HOST")
    if not host:
        # Mode pengembangan: tanpa SMTP, kode ditampilkan di terminal server.
        print(f"\n[PERI] Kode verifikasi untuk {tujuan}: {kode} (berlaku 10 menit)\n", flush=True)
        return
    msg = EmailMessage()
    msg["Subject"] = "Kode verifikasi PERI"
    msg["From"] = os.environ.get("PERI_SMTP_FROM", os.environ.get("PERI_SMTP_USER", "no-reply@peri.local"))
    msg["To"] = tujuan
    msg.set_content(f"Kode verifikasi Anda: {kode}\nBerlaku 10 menit. Abaikan email ini jika Anda tidak mendaftar.")
    with smtplib.SMTP(host, int(os.environ.get("PERI_SMTP_PORT", "587")), timeout=15) as s:
        s.starttls()
        if os.environ.get("PERI_SMTP_USER"):
            s.login(os.environ["PERI_SMTP_USER"], os.environ.get("PERI_SMTP_PASS", ""))
        s.send_message(msg)


_gagal = {}  # kunci (email|ip) -> (jumlah, waktu_mulai)


def _kunci_login(email):
    return f"{email}|{request.remote_addr}"


def terkunci(email):
    n, t = _gagal.get(_kunci_login(email), (0, 0))
    if n >= LOGIN_MAKS_GAGAL and time.time() - t < LOGIN_KUNCI:
        return True
    if n and time.time() - t >= LOGIN_KUNCI:
        _gagal.pop(_kunci_login(email), None)
    return False


def catat_gagal(email):
    k = _kunci_login(email)
    n, t = _gagal.get(k, (0, time.time()))
    _gagal[k] = (n + 1, t)


# ------------------------------------------------------------------ routes
@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/auth/kirim-kode")
def kirim_kode():
    email = norm_email(json_body().get("email"))
    if not EMAIL_RE.match(email):
        return galat("Masukkan email yang valid.")
    if db().execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        return galat("Email sudah terdaftar. Silakan masuk.", 409)
    row = db().execute("SELECT dikirim FROM kode_verifikasi WHERE email = ?", (email,)).fetchone()
    if row and time.time() - row["dikirim"] < KODE_JEDA_KIRIM:
        sisa = int(KODE_JEDA_KIRIM - (time.time() - row["dikirim"])) + 1
        return galat(f"Tunggu {sisa} detik sebelum meminta kode lagi.", 429)
    kode = f"{secrets.randbelow(10**6):06d}"
    now = time.time()
    db().execute(
        "INSERT INTO kode_verifikasi (email, kode_hash, kedaluwarsa, percobaan, dikirim) "
        "VALUES (?, ?, ?, 0, ?) ON CONFLICT(email) DO UPDATE SET "
        "kode_hash = excluded.kode_hash, kedaluwarsa = excluded.kedaluwarsa, "
        "percobaan = 0, dikirim = excluded.dikirim",
        (email, hash_kode(email, kode), now + KODE_BERLAKU, now),
    )
    db().commit()
    try:
        kirim_email(email, kode)
    except Exception as exc:  # SMTP salah konfigurasi / tidak terjangkau
        print(f"[PERI] Gagal mengirim email: {exc}", flush=True)
        return galat("Kode belum bisa dikirim. Coba lagi nanti.", 502)
    return jsonify(ok=True, berlaku_detik=KODE_BERLAKU)


@app.post("/api/auth/register")
def register():
    d = json_body()
    email = norm_email(d.get("email"))
    kode = d.get("kode").strip() if isinstance(d.get("kode"), str) else ""
    pw = d.get("password")
    if not EMAIL_RE.match(email):
        return galat("Masukkan email yang valid.")
    if not kode:
        return galat("Masukkan kode verifikasi.")
    if not isinstance(pw, str) or not 8 <= len(pw) <= 30:
        return galat("Kata sandi 8–30 karakter.")

    row = db().execute("SELECT * FROM kode_verifikasi WHERE email = ?", (email,)).fetchone()
    if not row or time.time() > row["kedaluwarsa"]:
        return galat("Kode verifikasi tidak ada atau sudah kedaluwarsa. Klik Resend.")
    if row["percobaan"] >= KODE_MAKS_COBA:
        return galat("Terlalu banyak percobaan. Klik Resend untuk kode baru.", 429)
    if not hmac.compare_digest(row["kode_hash"], hash_kode(email, kode)):
        db().execute("UPDATE kode_verifikasi SET percobaan = percobaan + 1 WHERE email = ?", (email,))
        db().commit()
        return galat("Kode verifikasi salah.")

    try:
        # Role sengaja tidak dibaca dari permintaan: pendaftaran publik selalu 'pendaftar'.
        cur = db().execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'pendaftar')",
            (email, generate_password_hash(pw)),
        )
    except sqlite3.IntegrityError:
        return galat("Email sudah terdaftar. Silakan masuk.", 409)
    db().execute("DELETE FROM kode_verifikasi WHERE email = ?", (email,))
    db().commit()

    session.clear()
    session["uid"] = cur.lastrowid
    session.permanent = True
    return jsonify(user={"email": email, "role": "pendaftar"}), 201


_DUMMY_HASH = generate_password_hash("tidak-dipakai")


@app.post("/api/auth/login")
def login():
    d = json_body()
    email = norm_email(d.get("email"))
    pw = d.get("password")
    if not EMAIL_RE.match(email) or not isinstance(pw, str) or not pw:
        return galat("Email atau kata sandi salah.", 401)
    if terkunci(email):
        return galat("Terlalu banyak percobaan gagal. Coba lagi beberapa menit lagi.", 429)

    row = db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    ok = check_password_hash(row["password_hash"] if row else _DUMMY_HASH, pw)
    if not (row and ok):
        catat_gagal(email)
        return galat("Email atau kata sandi salah.", 401)

    _gagal.pop(_kunci_login(email), None)
    session.clear()
    session["uid"] = row["id"]
    session.permanent = True
    return jsonify(user=user_publik(row))


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/auth/me")
def me():
    u = user_saat_ini()
    if not u:
        return galat("Belum masuk.", 401)
    return jsonify(user=user_publik(u))


def admin_required(fn):
    """Hanya akun ber-role admin (dicek di server, bukan di browser)."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*a, **kw):
        u = user_saat_ini()
        if not u:
            return galat("Belum masuk.", 401)
        if u["role"] != "admin":
            return galat("Khusus admin.", 403)
        return fn(*a, **kw)

    return wrapper


_kirim_log = {}  # ip -> [waktu, ...]


def terlalu_sering():
    now = time.time()
    log = [t for t in _kirim_log.get(request.remote_addr, []) if now - t < KIRIM_JENDELA]
    if len(log) >= KIRIM_MAKS:
        _kirim_log[request.remote_addr] = log
        return True
    log.append(now)
    _kirim_log[request.remote_addr] = log
    return False


@app.post("/api/buku-tamu")
def kirim_umpan_balik():
    """Form Umpan Balik di web lembaga (publik, tanpa login)."""
    d = json_body()
    nama = d.get("nama", "").strip() if isinstance(d.get("nama"), str) else ""
    email = norm_email(d.get("email"))
    kategori = d.get("kategori")
    pesan = d.get("pesan", "").strip() if isinstance(d.get("pesan"), str) else ""
    if not nama or len(nama) > 100:
        return galat("Nama wajib diisi (maks. 100 karakter).")
    if not EMAIL_RE.match(email) or len(email) > 150:
        return galat("Masukkan email yang valid.")
    if kategori not in KATEGORI_BUKU_TAMU:
        return galat("Pilih kategori umpan balik.")
    if not pesan or len(pesan) > 2000:
        return galat("Pesan wajib diisi (maks. 2000 karakter).")
    if terlalu_sering():
        return galat("Terlalu banyak pesan dalam waktu singkat. Coba lagi nanti.", 429)
    db().execute(
        "INSERT INTO buku_tamu (nama, email, kategori, pesan) VALUES (?, ?, ?, ?)",
        (nama, email, kategori, pesan),
    )
    db().commit()
    return jsonify(ok=True), 201


@app.get("/api/buku-tamu")
@admin_required
def daftar_buku_tamu():
    rows = db().execute(
        "SELECT id, nama, email, kategori, pesan, dibaca, substr(dibuat, 1, 10) AS tanggal "
        "FROM buku_tamu ORDER BY id DESC"
    ).fetchall()
    return jsonify(pesan=[{**dict(r), "dibaca": bool(r["dibaca"])} for r in rows])


@app.post("/api/buku-tamu/<int:pid>/dibaca")
@admin_required
def tandai_dibaca(pid):
    nilai = json_body().get("dibaca")
    if not isinstance(nilai, bool):
        return galat("'dibaca' harus true atau false.")
    cur = db().execute("UPDATE buku_tamu SET dibaca = ? WHERE id = ?", (int(nilai), pid))
    db().commit()
    if cur.rowcount == 0:
        return galat("Pesan tidak ditemukan.", 404)
    return jsonify(ok=True)


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)