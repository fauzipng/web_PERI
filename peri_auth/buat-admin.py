"""Menambah / menjadikan akun sebagai ADMIN langsung di database.

Contoh (dari folder peri-auth):
    python buat_admin.py admin@peri.id            # kata sandi ditanyakan
    python buat_admin.py admin@peri.id --naikkan  # jadikan akun yang sudah ada sebagai admin
    python buat_admin.py admin@peri.id --turunkan # kembalikan ke pendaftar

Alternatif tanpa skrip: daftar lewat web, lalu di DB Browser for SQLite jalankan
    UPDATE users SET role = 'admin' WHERE email = 'admin@peri.id';
"""
import getpass
import sqlite3
import sys

from werkzeug.security import generate_password_hash

import app as peri  # memakai DB_PATH yang sama dan memastikan tabel ada


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 1
    email = argv[0].strip().lower()
    conn = sqlite3.connect(peri.DB_PATH)
    ada = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()

    if "--turunkan" in argv or "--naikkan" in argv:
        if not ada:
            print(f"Akun {email} tidak ditemukan.")
            return 1
        role = "pendaftar" if "--turunkan" in argv else "admin"
        conn.execute("UPDATE users SET role = ? WHERE email = ?", (role, email))
        conn.commit()
        print(f"Role {email} sekarang: {role}")
        return 0

    if ada:
        print(f"{email} sudah terdaftar. Pakai --naikkan untuk menjadikannya admin.")
        return 1
    pw = getpass.getpass("Kata sandi admin (8-30 karakter): ")
    if not 8 <= len(pw) <= 30:
        print("Kata sandi harus 8-30 karakter.")
        return 1
    if pw != getpass.getpass("Ulangi kata sandi: "):
        print("Kata sandi tidak sama.")
        return 1
    conn.execute(
        "INSERT INTO users (email, password_hash, role) VALUES (?, ?, 'admin')",
        (email, generate_password_hash(pw)),
    )
    conn.commit()
    print(f"Admin {email} dibuat.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))